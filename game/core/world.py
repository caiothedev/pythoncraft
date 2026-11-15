import json
import random
from pathlib import Path

from perlin_noise import PerlinNoise
from ursina import Entity, Mesh, Vec2, Vec3, Vec4, color, destroy

from game.blocks import (
    BLOCK_TYPE_INTERACTIVE,
    BLOCK_TYPE_LIQUID,
    BLOCK_TYPE_SOLID,
    get_block,
)

# Configurações
CHUNK_SIZE  = 16   # blocos por chunk (X e Z)
RENDER_DIST = 10    # chunks visíveis em cada direção a partir do jogador
WORLD_BOTTOM = -3  # camada mais baixa do mundo

noise = PerlinNoise(octaves=4, seed=0)

world_parent  = Entity()
placed_blocks: dict[tuple, str] = {}   # (x,y,z) → block_id string
_chunk_entities: dict[tuple, Entity] = {}  # (cx,cz) → entity da mesh
_colliders: dict[tuple, Entity] = {}      # (x,y,z) → colisor invisível do bloco
_blocks_by_chunk: dict[tuple, set[tuple]] = {}
_blocks_by_column: dict[tuple, set[int]] = {}
_loaded_chunks: set[tuple] = set()
_modified_blocks: dict[tuple, str | None] = {}
_world_size = 0
_max_height = 6
_render_distance = 1
_world_seed = 0
_light_level = 1.0                         # brilho do mundo (ciclo dia/noite)

_NEIGHBOR_OFFSETS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

# Geração de altura
def get_height(x: int, z: int, scale: float = 20, amplitude: int = 6) -> int:
    value = noise([x / scale, z / scale])
    return int(((value + 1) / 2) * amplitude)

def _block_id_for_layer(y: int, surface_y: int) -> str:
    if y == surface_y:
        return "grass"
    elif y > surface_y - 3:
        return "dirt"
    else:
        return "stone"

# Faces do cubo — direção, normal, vértices, UV, vizinho
#  Cada face: (nome, vizinho_offset, vértices em ordem quad, rotação_euler_para_UV)
#  Os vértices já estão em espaço local do bloco (centro = 0,0,0).

_HALF = 0.5

_UV_TOP  = [Vec2(0,0), Vec2(1,0), Vec2(1,1), Vec2(0,1)]
_UV_SIDE = [Vec2(0,0), Vec2(0,1), Vec2(1,1), Vec2(1,0)]

_FACE_BRIGHTNESS = {
    "top":    Vec4(1.00, 1.00, 1.00, 1),
    "bottom": Vec4(0.55, 0.55, 0.55, 1),
    "front":  Vec4(0.80, 0.80, 0.80, 1),
    "back":   Vec4(0.70, 0.70, 0.70, 1),
    "right":  Vec4(0.90, 0.90, 0.90, 1),
    "left":   Vec4(0.60, 0.60, 0.60, 1),
}

_FACES = [
    # name,   offset,       4 vértices (x,y,z)
    ("top",    ( 0,  1,  0), [
        Vec3(-_HALF,  _HALF, -_HALF),
        Vec3( _HALF,  _HALF, -_HALF),
        Vec3( _HALF,  _HALF,  _HALF),
        Vec3(-_HALF,  _HALF,  _HALF),
    ], _UV_TOP),
    ("bottom", ( 0, -1,  0), [
        Vec3(-_HALF, -_HALF,  _HALF),
        Vec3( _HALF, -_HALF,  _HALF),
        Vec3( _HALF, -_HALF, -_HALF),
        Vec3(-_HALF, -_HALF, -_HALF),
    ], _UV_TOP),
    ("front",  ( 0,  0,  1), [
        Vec3(-_HALF, -_HALF,  _HALF),
        Vec3(-_HALF,  _HALF,  _HALF),
        Vec3( _HALF,  _HALF,  _HALF),
        Vec3( _HALF, -_HALF,  _HALF),
    ], _UV_SIDE),
    ("back",   ( 0,  0, -1), [
        Vec3( _HALF, -_HALF, -_HALF),
        Vec3( _HALF,  _HALF, -_HALF),
        Vec3(-_HALF,  _HALF, -_HALF),
        Vec3(-_HALF, -_HALF, -_HALF),
    ], _UV_SIDE),
    ("right",  ( 1,  0,  0), [
        Vec3( _HALF, -_HALF,  _HALF),
        Vec3( _HALF,  _HALF,  _HALF),
        Vec3( _HALF,  _HALF, -_HALF),
        Vec3( _HALF, -_HALF, -_HALF),
    ], _UV_SIDE),
    ("left",   (-1,  0,  0), [
        Vec3(-_HALF, -_HALF, -_HALF),
        Vec3(-_HALF,  _HALF, -_HALF),
        Vec3(-_HALF,  _HALF,  _HALF),
        Vec3(-_HALF, -_HALF,  _HALF),
    ], _UV_SIDE),
]

# UV de um quad inteiro
_QUAD_UVS = [
    Vec2(0, 0),
    Vec2(1, 0),
    Vec2(1, 1),
    Vec2(0, 1),
]

_SIDE_UVS = [
    Vec2(1, 0),
    Vec2(1, 1),
    Vec2(0, 1),
    Vec2(0, 0),
]

# 2 triângulos por quad (índices dentro dos 4 vértices da face)
_QUAD_TRIS = [0, 1, 2, 2, 3, 0]

# Iluminação básica por face (como no Minecraft): topo claro, laterais e fundo mais escuros
_FACE_SHADE = {
    "top": 1.0,
    "front": 0.8,
    "back": 0.8,
    "right": 0.65,
    "left": 0.65,
    "bottom": 0.5,
}

# Resolução de textura por face
def _face_texture(block, face_name: str):
    """Retorna a textura correta de acordo com o nome da face."""
    tex_map = block.textures          # dict com top/bottom/side
    if face_name == "top":
        return tex_map.get("top") or tex_map.get("side")
    elif face_name == "bottom":
        return tex_map.get("bottom") or tex_map.get("side")
    else:   # front / back / right / left  → side
        return tex_map.get("side") or tex_map.get("top")

# Construção de mesh por grupo de textura dentro de um chunk
def _build_chunk_mesh(cx: int, cz: int) -> Entity:
    """
    Constrói uma Entity por textura única dentro do chunk.
    Retorna um Entity-pai que agrupa todas as sub-meshes.
    """
    # Acumula vértices/UVs/triângulos separados por textura
    tex_buckets: dict = {}   # texture_object → {verts, uvs, tris}

    for x, y, z in _blocks_by_chunk.get((cx, cz), ()):
        block_id = placed_blocks.get((x, y, z))
        if block_id is None:
            continue
        block = get_block(block_id)
        if block is None:
            continue

        for face_name, (dx, dy, dz), verts, face_uvs in _FACES:
            nx, ny, nz = x + dx, y + dy, z + dz

            # Só renderiza face se o vizinho estiver vazio (face culling)
            if placed_blocks.get((nx, ny, nz)) is not None:
                neighbor_block = get_block(placed_blocks[(nx, ny, nz)])
                # Blocos opacos ocultam a face — blocos transparentes não
                if neighbor_block and not neighbor_block.transparent:
                    continue

            tex = _face_texture(block, face_name)
            if tex is None:
                continue

            bucket = tex_buckets.setdefault(tex, {"verts": [], "uvs": [], "tris": [], "colors": []})
            shade = _FACE_SHADE[face_name]
            face_color = color.Color(shade, shade, shade, 1)

            base_idx = len(bucket["verts"])
            for v, uv in zip(verts, face_uvs):
                bucket["verts"].append(Vec3(v.x + x, v.y + y, v.z + z))
                bucket["uvs"].append(uv)
                bucket["colors"].append(face_color)
            for t in _QUAD_TRIS:
                bucket["tris"].append(base_idx + t)

    # Cria o entity-pai do chunk
    parent_entity = Entity(parent=world_parent)

    for tex, data in tex_buckets.items():
        if not data["verts"]:
            continue
        mesh = Mesh(
            vertices=data["verts"],
            uvs=data["uvs"],
            colors=data["colors"],
            triangles=data["tris"],
            mode="triangle",
        )
        Entity(
            parent=parent_entity,
            model=mesh,
            texture=tex,
            color=color.Color(_light_level, _light_level, _light_level, 1),
        )

    return parent_entity

def is_exposed(pos: tuple, blocks: dict) -> bool:
    """
    Um bloco precisa de colisor quando algum vizinho está vazio, ou seja,
    quando o jogador pode encostar nele ou mirar nele.
    O "vizinho" abaixo da camada mais baixa do mundo não conta.
    """
    x, y, z = pos
    for dx, dy, dz in _NEIGHBOR_OFFSETS:
        ny = y + dy
        if ny < WORLD_BOTTOM:
            continue
        if (x + dx, ny, z + dz) not in blocks:
            return True
    return False

def _update_collider(pos: tuple):
    """Cria ou remove o colisor de uma posição conforme ela esteja exposta."""
    needs_collider = pos in placed_blocks and is_exposed(pos, placed_blocks)
    has_collider = pos in _colliders

    if needs_collider and not has_collider:
        _colliders[pos] = Entity(
            parent=world_parent,
            position=pos,
            model="cube",
            collider="box",
            visible=False,
            color=color.clear,
        )
    elif has_collider and not needs_collider:
        destroy(_colliders.pop(pos))

def _spawn_all_colliders():
    """Cria colisores para todos os blocos expostos (usado ao gerar o mundo)."""
    for pos in placed_blocks:
        _update_collider(pos)

def _update_colliders_around(pos: tuple):
    """Atualiza o colisor da posição editada e dos 6 vizinhos."""
    x, y, z = pos
    _update_collider(pos)
    for dx, dy, dz in _NEIGHBOR_OFFSETS:
        _update_collider((x + dx, y + dy, z + dz))

# Geração de árvores e minérios

def _coordinate_seed(*values: int) -> int:
    value = _world_seed & 0xFFFFFFFF
    for part in values:
        value = (value * 1664525 + int(part) + 1013904223) & 0xFFFFFFFF
    return value


def _surface_y(x: int, z: int) -> int:
    return get_height(x, z, amplitude=_max_height)


def _is_tree_candidate(x: int, z: int) -> bool:
    if abs(x) <= 3 and abs(z) <= 3:
        return False
    rng = random.Random(_coordinate_seed(x, z, 17))
    return rng.random() <= 0.05


def _tree_positions_around(cx: int, cz: int) -> list[tuple[int, int]]:
    """Retorna árvores próximas ao chunk em ordem determinística."""
    x0 = cx * CHUNK_SIZE - 10
    x1 = (cx + 1) * CHUNK_SIZE + 10
    z0 = cz * CHUNK_SIZE - 10
    z1 = (cz + 1) * CHUNK_SIZE + 10
    candidates = [
        (x, z)
        for x in range(x0, x1)
        for z in range(z0, z1)
        if -_world_size <= x < _world_size
        and -_world_size <= z < _world_size
        and _is_tree_candidate(x, z)
        and _block_id_for_layer(_surface_y(x, z), _surface_y(x, z)) == "grass"
    ]
    candidates.sort()
    chosen: list[tuple[int, int]] = []
    for position in candidates:
        if all(
            (position[0] - other[0]) ** 2 + (position[1] - other[1]) ** 2 >= 64
            for other in chosen
        ):
            chosen.append(position)
    return chosen


def _tree_blocks(x: int, surface_y: int, z: int) -> dict[tuple[int, int, int], str]:
    rng = random.Random(_coordinate_seed(x, z, 29))
    trunk_height = rng.randint(4, 6)
    generated = {}

    for dy in range(1, trunk_height + 1):
        generated[(x, surface_y + dy, z)] = "oak_log"

    top_y = surface_y + trunk_height
    for dy in range(-1, 3):
        radius = 2 if dy < 1 else 1
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                if dx == 0 and dz == 0 and dy < 1:
                    continue
                generated.setdefault((x + dx, top_y + dy, z + dz), "oak_leaves")
    return generated


def _ore_for_block(x: int, y: int, z: int, surface_y: int) -> str:
    ore_table = (
        ("coal_ore", 0.04, -2),
        ("iron_ore", 0.02, -4),
        ("gold_ore", 0.01, -6),
        ("diamond_ore", 0.004, -8),
    )
    rng = random.Random(_coordinate_seed(x, y, z, 41))
    for ore_id, probability, max_relative_y in ore_table:
        if y <= surface_y + max_relative_y and rng.random() < probability:
            return ore_id
    return "stone"


def _generated_chunk_blocks(cx: int, cz: int) -> dict[tuple[int, int, int], str]:
    """Gera apenas um chunk e suas árvores que alcançam esse chunk."""
    x0 = max(-_world_size, cx * CHUNK_SIZE)
    x1 = min(_world_size, (cx + 1) * CHUNK_SIZE)
    z0 = max(-_world_size, cz * CHUNK_SIZE)
    z1 = min(_world_size, (cz + 1) * CHUNK_SIZE)
    generated = {}

    for x in range(x0, x1):
        for z in range(z0, z1):
            surface_y = _surface_y(x, z)
            for y in range(WORLD_BOTTOM, surface_y + 1):
                block_id = _block_id_for_layer(y, surface_y)
                if block_id == "stone":
                    block_id = _ore_for_block(x, y, z, surface_y)
                generated[(x, y, z)] = block_id

    for tree_x, tree_z in _tree_positions_around(cx, cz):
        for position, block_id in _tree_blocks(tree_x, _surface_y(tree_x, tree_z), tree_z).items():
            x, _, z = position
            if x0 <= x < x1 and z0 <= z < z1 and position not in generated:
                generated[position] = block_id
    return generated


def _index_block(position: tuple[int, int, int], block_id: str):
    x, y, z = position
    chunk = (x // CHUNK_SIZE, z // CHUNK_SIZE)
    _blocks_by_chunk.setdefault(chunk, set()).add(position)
    _blocks_by_column.setdefault((x, z), set()).add(y)
    placed_blocks[position] = block_id


def _unindex_block(position: tuple[int, int, int]):
    x, y, z = position
    placed_blocks.pop(position, None)
    chunk = (x // CHUNK_SIZE, z // CHUNK_SIZE)
    positions = _blocks_by_chunk.get(chunk)
    if positions:
        positions.discard(position)
        if not positions:
            _blocks_by_chunk.pop(chunk, None)
    column = _blocks_by_column.get((x, z))
    if column:
        column.discard(y)
        if not column:
            _blocks_by_column.pop((x, z), None)


def _load_chunk(chunk: tuple[int, int]):
    if chunk in _loaded_chunks:
        return
    generated = _generated_chunk_blocks(*chunk)
    x0, z0 = chunk[0] * CHUNK_SIZE, chunk[1] * CHUNK_SIZE
    for position, block_id in _modified_blocks.items():
        x, _, z = position
        if x0 <= x < x0 + CHUNK_SIZE and z0 <= z < z0 + CHUNK_SIZE:
            if block_id is None:
                generated.pop(position, None)
            else:
                generated[position] = block_id
    for position, block_id in generated.items():
        _index_block(position, block_id)
    _loaded_chunks.add(chunk)
    _chunk_entities[chunk] = _build_chunk_mesh(*chunk)
    for position in generated:
        _update_collider(position)
    for neighbor in _neighbor_chunks(chunk):
        if neighbor in _loaded_chunks:
            _rebuild_loaded_chunk(neighbor)


def _unload_chunk(chunk: tuple[int, int]):
    if chunk not in _loaded_chunks:
        return
    entity = _chunk_entities.pop(chunk, None)
    if entity:
        destroy(entity)
    for position in list(_blocks_by_chunk.get(chunk, ())):
        collider = _colliders.pop(position, None)
        if collider:
            destroy(collider)
        _unindex_block(position)
    _loaded_chunks.remove(chunk)
    for neighbor in _neighbor_chunks(chunk):
        if neighbor in _loaded_chunks:
            _rebuild_loaded_chunk(neighbor)


def _neighbor_chunks(chunk: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    cx, cz = chunk
    return ((cx - 1, cz), (cx + 1, cz), (cx, cz - 1), (cx, cz + 1))


def _rebuild_loaded_chunk(chunk: tuple[int, int]):
    old_entity = _chunk_entities.pop(chunk, None)
    if old_entity:
        destroy(old_entity)
    _chunk_entities[chunk] = _build_chunk_mesh(*chunk)


# API pública
def clear_world(clear_modifications: bool = True):
    """Remove todos os blocos, meshes e colisores do mundo."""
    for c in list(world_parent.children):
        destroy(c)
    placed_blocks.clear()
    _chunk_entities.clear()
    _colliders.clear()
    _blocks_by_chunk.clear()
    _blocks_by_column.clear()
    _loaded_chunks.clear()
    if clear_modifications:
        _modified_blocks.clear()


def create_world(
    size: int = 16,
    max_height: int = 8,
    seed: int | None = None,
    render_distance: int = 1,
):
    """
    Inicializa um mundo finito e carrega apenas os chunks próximos da origem.
    `seed` torna relevo, árvores e minérios reproduzíveis.
    """
    if size <= 0:
        raise ValueError("size deve ser maior que zero")
    if max_height <= 0:
        raise ValueError("max_height deve ser maior que zero")
    if render_distance < 0:
        raise ValueError("render_distance não pode ser negativo")

    global noise, _world_size, _max_height, _render_distance, _world_seed
    clear_world()
    _world_size = size
    _max_height = max_height
    _render_distance = render_distance
    _world_seed = seed if seed is not None else random.SystemRandom().randint(0, 2**31 - 1)
    noise = PerlinNoise(octaves=4, seed=_world_seed)
    stream_world((0, 0, 0))
    return get_top_y(0, 0)


def _chunk_in_bounds(chunk: tuple[int, int]) -> bool:
    cx, cz = chunk
    return (
        cx * CHUNK_SIZE < _world_size
        and (cx + 1) * CHUNK_SIZE > -_world_size
        and cz * CHUNK_SIZE < _world_size
        and (cz + 1) * CHUNK_SIZE > -_world_size
    )


def stream_world(position, render_distance: int | None = None):
    """Carrega chunks próximos da posição e remove os que ficaram distantes."""
    distance = _render_distance if render_distance is None else render_distance
    center = (int(position[0]) // CHUNK_SIZE, int(position[2]) // CHUNK_SIZE)
    wanted = {
        (center[0] + dx, center[1] + dz)
        for dx in range(-distance, distance + 1)
        for dz in range(-distance, distance + 1)
    }
    wanted = {chunk for chunk in wanted if _chunk_in_bounds(chunk)}
    for chunk in sorted(wanted - _loaded_chunks):
        _load_chunk(chunk)
    for chunk in sorted(_loaded_chunks - wanted):
        _unload_chunk(chunk)


def get_loaded_chunks() -> set[tuple[int, int]]:
    return set(_loaded_chunks)


def get_world_seed() -> int:
    return _world_seed


def get_top_y(x: int, z: int) -> int:
    """Altura do bloco mais alto na coluna, usando o índice da coluna."""
    column = _blocks_by_column.get((x, z))
    return max(column) if column else _surface_y(x, z)


def save_world(path: str | Path):
    """Salva a configuração do mundo e apenas os blocos alterados."""
    if _world_size <= 0:
        raise RuntimeError("nenhum mundo foi inicializado")
    changes = [
        {"x": x, "y": y, "z": z, "block": block_id}
        for (x, y, z), block_id in _modified_blocks.items()
    ]
    payload = {
        "version": 1,
        "seed": _world_seed,
        "size": _world_size,
        "max_height": _max_height,
        "render_distance": _render_distance,
        "changes": changes,
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_world(path: str | Path):
    """Carrega um mundo salvo e reconstitui os chunks iniciais."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != 1:
        raise ValueError("versão de mundo não suportada")

    changes = {}
    for change in payload.get("changes", []):
        position = (int(change["x"]), int(change["y"]), int(change["z"]))
        block_id = change.get("block")
        if block_id is not None and get_block(block_id) is None:
            raise ValueError(f"bloco desconhecido no save: {block_id}")
        changes[position] = block_id

    size = int(payload["size"])
    max_height = int(payload["max_height"])
    render_distance = int(payload.get("render_distance", 1))
    seed = int(payload["seed"])

    global noise, _world_size, _max_height, _render_distance, _world_seed
    clear_world(clear_modifications=False)
    _modified_blocks.clear()
    _modified_blocks.update(changes)
    _world_size = size
    _max_height = max_height
    _render_distance = render_distance
    _world_seed = seed
    noise = PerlinNoise(octaves=4, seed=_world_seed)
    stream_world((0, 0, 0))
    return get_top_y(0, 0)

def set_light_level(level: float):
    """
    Ajusta o brilho de todas as malhas do mundo (0 a 1).
    A Ursina desliga a herança de cor entre entidades, então a cor é aplicada em cada malha.
    """
    global _light_level
    if abs(level - _light_level) < 0.005:
        return
    _light_level = level
    light = color.Color(level, level, level, 1)
    for chunk in _chunk_entities.values():
        for mesh_entity in chunk.children:
            mesh_entity.color = light

def get_light_level() -> float:
    return _light_level

def get_block_at(pos: tuple) -> str | None:
    """ID do bloco na posição (x, y, z), ou None se estiver vazia."""
    return placed_blocks.get((int(pos[0]), int(pos[1]), int(pos[2])))

def is_solid_at(pos: tuple) -> bool:
    """True se o bloco na posição (x, y, z) inteira bloqueia o jogador (líquidos e efeitos não bloqueiam)."""
    block_id = placed_blocks.get(pos)
    if block_id is None:
        return False
    block = get_block(block_id)
    return block is not None and block.type in (BLOCK_TYPE_SOLID, BLOCK_TYPE_INTERACTIVE)

def is_liquid_at(pos: tuple) -> bool:
    """True se o bloco na posição (x, y, z) inteira é um líquido (água, lava...)."""
    block_id = placed_blocks.get(pos)
    block = get_block(block_id) if block_id else None
    return block is not None and block.type == BLOCK_TYPE_LIQUID

def break_block(pos: tuple) -> bool:
    """
    Remove o bloco na posição (x, y, z) do mundo.
    Reconstrói o chunk afetado. Retorna True se o bloco existia.
    """
    x, y, z = int(pos[0]), int(pos[1]), int(pos[2])
    key = (x, y, z)
    if key not in placed_blocks:
        return False
    _unindex_block(key)
    _modified_blocks[key] = None
    rebuild_chunk_at(key)
    _update_colliders_around(key)
    return True
 
 
def place_block(pos: tuple, block_id: str) -> bool:
    """
    Coloca um bloco na posição (x, y, z) do mundo.
    Reconstrói o chunk afetado. Retorna True se a posição estava vazia.
    """
    x, y, z = int(pos[0]), int(pos[1]), int(pos[2])
    key = (x, y, z)
    if key in placed_blocks or not (-_world_size <= x < _world_size and -_world_size <= z < _world_size):
        return False
    if get_block(block_id) is None:
        return False
    _index_block(key, block_id)
    _modified_blocks[key] = block_id
    rebuild_chunk_at(key)
    _update_colliders_around(key)
    return True

def chunks_to_rebuild(world_pos: tuple) -> set:
    """
    Chunks afetados por uma edição em (x, y, z): o próprio chunk e, se o bloco
    estiver na borda, o chunk vizinho (cuja face encostada pode aparecer/sumir).
    """
    x, _, z = (int(v) for v in world_pos)
    cx, cz = x // CHUNK_SIZE, z // CHUNK_SIZE
    chunks = {(cx, cz)}
    lx, lz = x % CHUNK_SIZE, z % CHUNK_SIZE
    if lx == 0:
        chunks.add((cx - 1, cz))
    elif lx == CHUNK_SIZE - 1:
        chunks.add((cx + 1, cz))
    if lz == 0:
        chunks.add((cx, cz - 1))
    elif lz == CHUNK_SIZE - 1:
        chunks.add((cx, cz + 1))
    return chunks

def rebuild_chunk_at(world_pos: tuple):
    """Reconstrói o(s) chunk(s) afetado(s) por uma edição em (x, y, z)."""
    for key in chunks_to_rebuild(world_pos):
        if key in _chunk_entities:
            _rebuild_loaded_chunk(key)