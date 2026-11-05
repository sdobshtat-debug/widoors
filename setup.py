import os
FILES = {'src/main/java/ua/widedoors/WideDoorBlock.java': 'package ua.widedoors;\n\nimport net.minecraft.block.Block;\nimport net.minecraft.block.BlockState;\nimport net.minecraft.block.Blocks;\nimport net.minecraft.block.ShapeContext;\nimport net.minecraft.entity.LivingEntity;\nimport net.minecraft.entity.player.PlayerEntity;\nimport net.minecraft.item.ItemPlacementContext;\nimport net.minecraft.item.ItemStack;\nimport net.minecraft.sound.SoundCategory;\nimport net.minecraft.sound.SoundEvent;\nimport net.minecraft.state.StateManager;\nimport net.minecraft.state.property.BooleanProperty;\nimport net.minecraft.state.property.EnumProperty;\nimport net.minecraft.state.property.IntProperty;\nimport net.minecraft.state.property.Properties;\nimport net.minecraft.util.ActionResult;\nimport net.minecraft.util.hit.BlockHitResult;\nimport net.minecraft.util.math.BlockPos;\nimport net.minecraft.util.math.Direction;\nimport net.minecraft.util.shape.VoxelShape;\nimport net.minecraft.util.shape.VoxelShapes;\nimport net.minecraft.world.BlockView;\nimport net.minecraft.world.World;\nimport net.minecraft.world.block.WireOrientation;\nimport org.jetbrains.annotations.Nullable;\n\n/**\n * Великі двері 3 блоки завширшки і 3 блоки заввишки, дві стулки.\n * Кожен з 9 блоків - це окремий блок цього класу зі станом COL (0..2) і ROW (0..2).\n * COL 0 - лівий стовпець (якщо дивитися на двері з боку гравця, який їх ставив), COL 2 - правий.\n * Ставляться вони так, що блок, у який ви ставите, стає НИЖНІМ СЕРЕДНІМ (col=1, row=0).\n */\npublic class WideDoorBlock extends Block {\n    public static final EnumProperty<Direction> FACING = Properties.HORIZONTAL_FACING;\n    public static final IntProperty COL = IntProperty.of("col", 0, 2);\n    public static final IntProperty ROW = IntProperty.of("row", 0, 2);\n    public static final BooleanProperty OPEN = Properties.OPEN;\n    public static final BooleanProperty POWERED = Properties.POWERED;\n\n    private static final Direction[] DIRS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};\n\n    // Форми для напрямку NORTH (панель біля південного краю блока), для інших напрямків повертаємо.\n    private static final VoxelShape[] CLOSED = new VoxelShape[4];\n    private static final VoxelShape[] LEAF_LEFT = new VoxelShape[4];\n    private static final VoxelShape[] LEAF_RIGHT = new VoxelShape[4];\n\n    static {\n        for (int i = 0; i < 4; i++) {\n            CLOSED[i] = rotated(0, 13, 16, 16, i);\n            LEAF_LEFT[i] = rotated(0, 0, 3, 16, i);\n            LEAF_RIGHT[i] = rotated(13, 0, 16, 16, i);\n        }\n    }\n\n    private final boolean handOpen;\n    private final SoundEvent openSound;\n    private final SoundEvent closeSound;\n\n    public WideDoorBlock(Settings settings, boolean handOpen, SoundEvent openSound, SoundEvent closeSound) {\n        super(settings);\n        this.handOpen = handOpen;\n        this.openSound = openSound;\n        this.closeSound = closeSound;\n        this.setDefaultState(this.getStateManager().getDefaultState()\n                .with(FACING, Direction.NORTH)\n                .with(COL, 1)\n                .with(ROW, 0)\n                .with(OPEN, false)\n                .with(POWERED, false));\n    }\n\n    // ---------- допоміжні функції геометрії ----------\n\n    /** Поворот прямокутника (у координатах 0..16) на turns чвертей за годинниковою стрілкою. */\n    private static VoxelShape rotated(double x1, double z1, double x2, double z2, int turns) {\n        for (int i = 0; i < turns; i++) {\n            double nx1 = 16 - z2;\n            double nx2 = 16 - z1;\n            double nz1 = x1;\n            double nz2 = x2;\n            x1 = nx1;\n            x2 = nx2;\n            z1 = nz1;\n            z2 = nz2;\n        }\n        return Block.createCuboidShape(x1, 0, z1, x2, 16, z2);\n    }\n\n    private static int idx(Direction d) {\n        return switch (d) {\n            case EAST -> 1;\n            case SOUTH -> 2;\n            case WEST -> 3;\n            default -> 0;\n        };\n    }\n\n    /** Позиція нижнього середнього блока для частини, що стоїть у pos. */\n    private static BlockPos base(BlockPos pos, BlockState state) {\n        Direction left = state.get(FACING).rotateYCounterclockwise();\n        return pos.down(state.get(ROW)).offset(left, state.get(COL) - 1);\n    }\n\n    /** Позиція частини (c, r) відносно нижнього середнього блока. */\n    private static BlockPos partPos(BlockPos base, Direction facing, int c, int r) {\n        Direction left = facing.rotateYCounterclockwise();\n        return base.offset(left, 1 - c).up(r);\n    }\n\n    // ---------- стани ----------\n\n    @Override\n    protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {\n        builder.add(FACING, COL, ROW, OPEN, POWERED);\n    }\n\n    @Override\n    public BlockState getPlacementState(ItemPlacementContext ctx) {\n        World world = ctx.getWorld();\n        BlockPos origin = ctx.getBlockPos();\n        Direction facing = ctx.getHorizontalPlayerFacing();\n        for (int c = 0; c < 3; c++) {\n            for (int r = 0; r < 3; r++) {\n                BlockPos p = partPos(origin, facing, c, r);\n                if (world.isOutOfHeightLimit(p) || !world.getBlockState(p).canReplace(ctx)) {\n                    return null;\n                }\n            }\n        }\n        return this.getDefaultState().with(FACING, facing).with(COL, 1).with(ROW, 0);\n    }\n\n    @Override\n    public void onPlaced(World world, BlockPos pos, BlockState state, @Nullable LivingEntity placer, ItemStack itemStack) {\n        if (world.isClient()) {\n            return;\n        }\n        Direction facing = state.get(FACING);\n        for (int c = 0; c < 3; c++) {\n            for (int r = 0; r < 3; r++) {\n                if (c == 1 && r == 0) {\n                    continue;\n                }\n                world.setBlockState(partPos(pos, facing, c, r),\n                        this.getDefaultState().with(FACING, facing).with(COL, c).with(ROW, r),\n                        Block.NOTIFY_ALL);\n            }\n        }\n        updatePower(world, pos, state);\n    }\n\n    // ---------- відкривання ----------\n\n    private void setAll(World world, BlockPos base, Direction facing, boolean open, boolean powered) {\n        for (int c = 0; c < 3; c++) {\n            for (int r = 0; r < 3; r++) {\n                BlockPos p = partPos(base, facing, c, r);\n                BlockState s = world.getBlockState(p);\n                if (s.isOf(this) && s.get(FACING) == facing) {\n                    world.setBlockState(p, s.with(OPEN, open).with(POWERED, powered),\n                            Block.NOTIFY_LISTENERS | Block.REDRAW_ON_MAIN_THREAD);\n                }\n            }\n        }\n    }\n\n    private void playToggleSound(World world, BlockPos pos, boolean open) {\n        world.playSound(null, pos, open ? openSound : closeSound, SoundCategory.BLOCKS,\n                1.0f, world.getRandom().nextFloat() * 0.1f + 0.9f);\n    }\n\n    @Override\n    public ActionResult onUse(BlockState state, World world, BlockPos pos, PlayerEntity player, BlockHitResult hit) {\n        if (!handOpen) {\n            return ActionResult.PASS; // залізні двері - тільки редстоун\n        }\n        if (!world.isClient()) {\n            boolean open = !state.get(OPEN);\n            setAll(world, base(pos, state), state.get(FACING), open, state.get(POWERED));\n            playToggleSound(world, pos, open);\n        }\n        return ActionResult.SUCCESS;\n    }\n\n    private void updatePower(World world, BlockPos pos, BlockState state) {\n        Direction facing = state.get(FACING);\n        BlockPos base = base(pos, state);\n        boolean powered = false;\n        for (int c = 0; c < 3 && !powered; c++) {\n            for (int r = 0; r < 3 && !powered; r++) {\n                powered = world.isReceivingRedstonePower(partPos(base, facing, c, r));\n            }\n        }\n        if (powered != state.get(POWERED)) {\n            if (powered != state.get(OPEN)) {\n                playToggleSound(world, pos, powered);\n            }\n            setAll(world, base, facing, powered, powered);\n        }\n    }\n\n    @Override\n    public void neighborUpdate(BlockState state, World world, BlockPos pos, Block sourceBlock,\n                               @Nullable WireOrientation wireOrientation, boolean notify) {\n        if (world.isClient() || sourceBlock == this) {\n            return;\n        }\n        updatePower(world, pos, state);\n    }\n\n    // ---------- ламання ----------\n\n    @Override\n    public BlockState onBreak(World world, BlockPos pos, BlockState state, PlayerEntity player) {\n        if (!world.isClient()) {\n            Direction facing = state.get(FACING);\n            BlockPos base = base(pos, state);\n            for (int c = 0; c < 3; c++) {\n                for (int r = 0; r < 3; r++) {\n                    BlockPos p = partPos(base, facing, c, r);\n                    if (p.equals(pos)) {\n                        continue;\n                    }\n                    BlockState s = world.getBlockState(p);\n                    if (s.isOf(this) && s.get(FACING) == facing) {\n                        world.setBlockState(p, Blocks.AIR.getDefaultState(), Block.NOTIFY_ALL | Block.SKIP_DROPS);\n                    }\n                }\n            }\n            if (!player.isCreative()) {\n                Block.dropStack(world, pos, new ItemStack(this));\n            }\n        }\n        return super.onBreak(world, pos, state, player);\n    }\n\n    // ---------- форми ----------\n\n    @Override\n    public VoxelShape getCollisionShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {\n        int i = idx(state.get(FACING));\n        if (!state.get(OPEN)) {\n            return CLOSED[i];\n        }\n        return switch (state.get(COL)) {\n            case 0 -> LEAF_LEFT[i];\n            case 2 -> LEAF_RIGHT[i];\n            default -> VoxelShapes.empty();\n        };\n    }\n\n    @Override\n    public VoxelShape getOutlineShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {\n        int i = idx(state.get(FACING));\n        if (!state.get(OPEN)) {\n            return CLOSED[i];\n        }\n        return switch (state.get(COL)) {\n            case 0 -> LEAF_LEFT[i];\n            case 2 -> LEAF_RIGHT[i];\n            default -> CLOSED[i]; // щоб у середній (порожній) частині можна було клікнути і закрити\n        };\n    }\n}\n', 'src/main/java/ua/widedoors/WideDoorsMod.java': 'package ua.widedoors;\n\nimport net.fabricmc.api.ModInitializer;\nimport net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;\nimport net.minecraft.block.AbstractBlock;\nimport net.minecraft.block.Block;\nimport net.minecraft.block.piston.PistonBehavior;\nimport net.minecraft.item.BlockItem;\nimport net.minecraft.item.Item;\nimport net.minecraft.item.ItemGroups;\nimport net.minecraft.registry.Registries;\nimport net.minecraft.registry.Registry;\nimport net.minecraft.registry.RegistryKey;\nimport net.minecraft.registry.RegistryKeys;\nimport net.minecraft.sound.BlockSoundGroup;\nimport net.minecraft.sound.SoundEvent;\nimport net.minecraft.sound.SoundEvents;\nimport net.minecraft.util.Identifier;\n\npublic class WideDoorsMod implements ModInitializer {\n    public static final String MOD_ID = "widedoors";\n\n    public static WideDoorBlock WIDE_OAK_DOOR;\n    public static WideDoorBlock WIDE_IRON_DOOR;\n    public static BlockItem WIDE_OAK_DOOR_ITEM;\n    public static BlockItem WIDE_IRON_DOOR_ITEM;\n\n    private static BlockItem lastItem;\n\n    private static WideDoorBlock register(String name, AbstractBlock.Settings settings, boolean handOpen,\n                                          SoundEvent open, SoundEvent close) {\n        Identifier id = Identifier.of(MOD_ID, name);\n\n        RegistryKey<Block> blockKey = RegistryKey.of(RegistryKeys.BLOCK, id);\n        WideDoorBlock block = new WideDoorBlock(settings.registryKey(blockKey), handOpen, open, close);\n        Registry.register(Registries.BLOCK, blockKey, block);\n\n        RegistryKey<Item> itemKey = RegistryKey.of(RegistryKeys.ITEM, id);\n        lastItem = new BlockItem(block, new Item.Settings().registryKey(itemKey).useBlockPrefixedTranslationKey());\n        Registry.register(Registries.ITEM, itemKey, lastItem);\n\n        return block;\n    }\n\n    @Override\n    public void onInitialize() {\n        WIDE_OAK_DOOR = register("wide_oak_door",\n                AbstractBlock.Settings.create()\n                        .strength(3.0f)\n                        .sounds(BlockSoundGroup.WOOD)\n                        .nonOpaque()\n                        .pistonBehavior(PistonBehavior.BLOCK),\n                true, SoundEvents.BLOCK_WOODEN_DOOR_OPEN, SoundEvents.BLOCK_WOODEN_DOOR_CLOSE);\n        WIDE_OAK_DOOR_ITEM = lastItem;\n\n        WIDE_IRON_DOOR = register("wide_iron_door",\n                AbstractBlock.Settings.create()\n                        .strength(5.0f)\n                        .sounds(BlockSoundGroup.METAL)\n                        .nonOpaque()\n                        .pistonBehavior(PistonBehavior.BLOCK),\n                false, SoundEvents.BLOCK_IRON_DOOR_OPEN, SoundEvents.BLOCK_IRON_DOOR_CLOSE);\n        WIDE_IRON_DOOR_ITEM = lastItem;\n\n        ItemGroupEvents.modifyEntriesEvent(ItemGroups.REDSTONE).register(entries -> {\n            entries.add(WIDE_OAK_DOOR_ITEM);\n            entries.add(WIDE_IRON_DOOR_ITEM);\n        });\n    }\n}\n', 'src/main/resources/fabric.mod.json': '{\n  "schemaVersion": 1,\n  "id": "widedoors",\n  "version": "${version}",\n  "name": "Wide Doors",\n  "description": "Великі двері 3x3 з двома стулками, що відкриваються.",\n  "authors": [],\n  "license": "MIT",\n  "icon": "assets/widedoors/icon.png",\n  "environment": "*",\n  "entrypoints": {\n    "main": ["ua.widedoors.WideDoorsMod"]\n  },\n  "depends": {\n    "fabricloader": ">=0.18.1",\n    "minecraft": "~1.21.11",\n    "java": ">=21",\n    "fabric-api": "*"\n  }\n}\n'}
for _p, _t in FILES.items():
    os.makedirs(os.path.dirname(_p), exist_ok=True)
    open(_p, 'w', encoding='utf-8').write(_t)
import json, os, random
from PIL import Image, ImageDraw

R = "src/main/resources"
A = f"{R}/assets/widedoors"
D = f"{R}/data"
def w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def jit(c, r, a=6):
    return tuple(max(0, min(255, v + r.randint(-a, a))) for v in c)

def make_tex(kind):
    rnd = random.Random(7 if kind == "wood" else 11)
    img = Image.new("RGBA", (48, 48))
    px = img.load()
    if kind == "wood":
        base, line, frame, rail, metal, hinge = (162,130,78),(140,110,64),(110,84,46),(120,92,50),(60,60,64),(50,50,54)
    else:
        base, line, frame, rail, metal, hinge = (196,198,203),(178,180,186),(140,142,150),(150,152,160),(90,92,98),(70,72,78)
    for y in range(48):
        for x in range(48):
            lx = x % 24  # координата всередині стулки
            c = base
            if kind == "wood":
                if lx % 4 == 0: c = line
                c = jit(c, rnd, 5)
            else:
                if y % 6 == 0: c = line
                c = jit(c, rnd, 3)
            px[x, y] = c + (255,)
    # рамка кожної стулки
    for leaf in (0, 24):
        for i in range(24):
            for t in range(2):
                for (x, y) in ((leaf+i, t), (leaf+i, 47-t), (leaf+t, i), (leaf+t, 47-i), (leaf+23-t, i), (leaf+23-t, 47-i)):
                    px[x, y] = jit(frame, rnd, 4) + (255,)
    # горизонтальна перекладина на середині + друга/третя
    for leaf in (0, 24):
        for yy in (15, 16, 31, 32):
            for x in range(leaf+2, leaf+22):
                px[x, yy] = jit(rail, rnd, 4) + (255,)
    # шов посередині
    for y in range(48):
        px[23, y] = (30,30,30,255) if kind == "wood" else (60,62,68,255)
        px[24, y] = (30,30,30,255) if kind == "wood" else (60,62,68,255)
    d = ImageDraw.Draw(img)
    # ручки
    d.rectangle([19, 21, 20, 26], fill=metal + (255,))
    d.rectangle([27, 21, 28, 26], fill=metal + (255,))
    # завіси
    for y in (5, 22, 39):
        d.rectangle([0, y, 3, y+3], fill=hinge + (255,))
        d.rectangle([44, y, 47, y+3], fill=hinge + (255,))
    if kind == "iron":
        for leaf in (0, 24):
            for yy in (5, 24, 42):
                for xx in (6, 17):
                    d.point((leaf+xx, yy), fill=(110,112,118,255))
    return img

for name, kind in (("wide_oak_door", "wood"), ("wide_iron_door", "iron")):
    t = make_tex(kind)
    os.makedirs(f"{A}/textures/block", exist_ok=True)
    os.makedirs(f"{A}/textures/item", exist_ok=True)
    t.save(f"{A}/textures/block/{name}.png")
    t.resize((16, 16), Image.BOX).save(f"{A}/textures/item/{name}.png")
    if name == "wide_oak_door":
        t.resize((64, 64), Image.NEAREST).save(f"{A}/icon.png")

S = 16/3  # одна колонка/рядок текстури 48x48 у одиницях UV (0..16)
def f6(x): return round(x, 5)

def closed_model(name, c, r):
    u1, u2 = c*S, (c+1)*S
    v1, v2 = (2-r)*S, (3-r)*S
    # північна грань дивиться з північного боку, там колонки дзеркальні (див. нотатки)
    nu1, nu2 = (2-c)*S, (3-c)*S
    faces = {
        "south": {"uv": [f6(u1), f6(v1), f6(u2), f6(v2)], "texture": "#door"},
        "north": {"uv": [f6(nu1), f6(v1), f6(nu2), f6(v2)], "texture": "#door"},
        "up":    {"uv": [f6(u1), 0, f6(u2), 0.5], "texture": "#door"},
        "down":  {"uv": [f6(u1), 0, f6(u2), 0.5], "texture": "#door"},
        "east":  {"uv": [0, f6(v1), 1, f6(v2)], "texture": "#door"},
        "west":  {"uv": [0, f6(v1), 1, f6(v2)], "texture": "#door"},
    }
    return {"textures": {"door": f"widedoors:block/{name}", "particle": f"widedoors:block/{name}"},
            "elements": [{"from": [0,0,13], "to": [16,16,16], "faces": faces}]}

def open_model(name, side, r):
    v1, v2 = (2-r)*S, (3-r)*S
    if side == "left":   # шарнір на x=0, лист у колонці 0 текстури
        frm, to = [0,0,0], [3,16,16]
        east = [0, f6(v1), f6(S), f6(v2)]
        west = [f6(S), f6(v1), 0, f6(v2)]
        edge = [0, 0, 0.5, 0.5]
    else:                # шарнір на x=16, колонка 2 текстури
        frm, to = [13,0,0], [16,16,16]
        east = [16, f6(v1), f6(16-S), f6(v2)]
        west = [f6(16-S), f6(v1), 16, f6(v2)]
        edge = [15.5, 0, 16, 0.5]
    faces = {
        "east": {"uv": east, "texture": "#door"},
        "west": {"uv": west, "texture": "#door"},
        "north": {"uv": [0, 0, 0.5, f6(S)], "texture": "#door"},
        "south": {"uv": [0, 0, 0.5, f6(S)], "texture": "#door"},
        "up": {"uv": edge, "texture": "#door"},
        "down": {"uv": edge, "texture": "#door"},
    }
    return {"textures": {"door": f"widedoors:block/{name}", "particle": f"widedoors:block/{name}"},
            "elements": [{"from": frm, "to": to, "faces": faces}]}

w(f"{A}/models/block/empty.json", {"textures": {"particle": "minecraft:block/oak_planks"}, "elements": []})

ROT = {"north": 0, "east": 90, "south": 180, "west": 270}
for name in ("wide_oak_door", "wide_iron_door"):
    variants = {}
    for c in range(3):
        for r in range(3):
            w(f"{A}/models/block/{name}_c{c}r{r}.json", closed_model(name, c, r))
    for r in range(3):
        w(f"{A}/models/block/{name}_open_left_r{r}.json", open_model(name, "left", r))
        w(f"{A}/models/block/{name}_open_right_r{r}.json", open_model(name, "right", r))
    for d, y in ROT.items():
        for c in range(3):
            for r in range(3):
                for o in ("false", "true"):
                    if o == "false":
                        m = f"widedoors:block/{name}_c{c}r{r}"
                    elif c == 0:
                        m = f"widedoors:block/{name}_open_left_r{r}"
                    elif c == 2:
                        m = f"widedoors:block/{name}_open_right_r{r}"
                    else:
                        m = "widedoors:block/empty"
                    variants[f"col={c},facing={d},open={o},row={r}"] = {"model": m, "y": y}
    w(f"{A}/blockstates/{name}.json", {"variants": variants})
    w(f"{A}/items/{name}.json", {"model": {"type": "minecraft:model", "model": f"widedoors:item/{name}"}})
    w(f"{A}/models/item/{name}.json", {"parent": "minecraft:item/generated", "textures": {"layer0": f"widedoors:item/{name}"}})

w(f"{A}/lang/en_us.json", {
    "block.widedoors.wide_oak_door": "Wide Oak Door",
    "block.widedoors.wide_iron_door": "Wide Iron Door"})
w(f"{A}/lang/uk_ua.json", {
    "block.widedoors.wide_oak_door": "Широкі дубові двері",
    "block.widedoors.wide_iron_door": "Широкі залізні двері"})

w(f"{D}/minecraft/tags/block/mineable/axe.json", {"replace": False, "values": ["widedoors:wide_oak_door"]})
w(f"{D}/minecraft/tags/block/mineable/pickaxe.json", {"replace": False, "values": ["widedoors:wide_iron_door"]})

w(f"{D}/widedoors/recipe/wide_oak_door.json", {
    "type": "minecraft:crafting_shaped", "category": "redstone",
    "key": {"P": "minecraft:oak_planks", "D": "minecraft:oak_door"},
    "pattern": ["PPP", "PDP", "PDP"],
    "result": {"id": "widedoors:wide_oak_door", "count": 1}})
w(f"{D}/widedoors/recipe/wide_iron_door.json", {
    "type": "minecraft:crafting_shaped", "category": "redstone",
    "key": {"P": "minecraft:iron_ingot", "D": "minecraft:iron_door"},
    "pattern": ["PPP", "PDP", "PDP"],
    "result": {"id": "widedoors:wide_iron_door", "count": 1}})
print("done")
