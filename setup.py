import os
FILES = {'src/main/java/ua/widedoors/WideDoorBlock.java': 'package ua.widedoors;\n\nimport net.minecraft.block.Block;\nimport net.minecraft.block.BlockState;\nimport net.minecraft.block.Blocks;\nimport net.minecraft.block.ShapeContext;\nimport net.minecraft.entity.LivingEntity;\nimport net.minecraft.entity.player.PlayerEntity;\nimport net.minecraft.item.ItemPlacementContext;\nimport net.minecraft.item.ItemStack;\nimport net.minecraft.sound.SoundCategory;\nimport net.minecraft.sound.SoundEvent;\nimport net.minecraft.state.StateManager;\nimport net.minecraft.state.property.BooleanProperty;\nimport net.minecraft.state.property.EnumProperty;\nimport net.minecraft.state.property.IntProperty;\nimport net.minecraft.state.property.Properties;\nimport net.minecraft.util.ActionResult;\nimport net.minecraft.util.hit.BlockHitResult;\nimport net.minecraft.util.math.BlockPos;\nimport net.minecraft.util.math.Direction;\nimport net.minecraft.util.shape.VoxelShape;\nimport net.minecraft.util.shape.VoxelShapes;\nimport net.minecraft.world.BlockView;\nimport net.minecraft.world.World;\nimport net.minecraft.world.block.WireOrientation;\nimport org.jetbrains.annotations.Nullable;\n\n/**\n * Великі двері 3 блоки завширшки і 3 блоки заввишки, дві стулки.\n * Кожен з 9 блоків - це окремий блок цього класу зі станом COL (0..2) і ROW (0..2).\n * COL 0 - лівий стовпець (якщо дивитися на двері з боку гравця, який їх ставив), COL 2 - правий.\n * Ставляться вони так, що блок, у який ви ставите, стає НИЖНІМ СЕРЕДНІМ (col=1, row=0).\n */\npublic class WideDoorBlock extends Block {\n    public static final EnumProperty<Direction> FACING = Properties.HORIZONTAL_FACING;\n    public static final IntProperty COL = IntProperty.of("col", 0, 2);\n    public static final IntProperty ROW = IntProperty.of("row", 0, 2);\n    public static final BooleanProperty OPEN = Properties.OPEN;\n    public static final BooleanProperty POWERED = Properties.POWERED;\n\n    private static final Direction[] DIRS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};\n\n    // Форми для напрямку NORTH (панель біля південного краю блока), для інших напрямків повертаємо.\n    private static final VoxelShape[] CLOSED = new VoxelShape[4];\n    private static final VoxelShape[] LEAF_LEFT = new VoxelShape[4];\n    private static final VoxelShape[] LEAF_RIGHT = new VoxelShape[4];\n\n    static {\n        for (int i = 0; i < 4; i++) {\n            CLOSED[i] = rotated(0, 13, 16, 16, i);\n            LEAF_LEFT[i] = rotated(0, 0, 3, 16, i);\n            LEAF_RIGHT[i] = rotated(13, 0, 16, 16, i);\n        }\n    }\n\n    private final boolean handOpen;\n    private final SoundEvent openSound;\n    private final SoundEvent closeSound;\n\n    public WideDoorBlock(Settings settings, boolean handOpen, SoundEvent openSound, SoundEvent closeSound) {\n        super(settings);\n        this.handOpen = handOpen;\n        this.openSound = openSound;\n        this.closeSound = closeSound;\n        this.setDefaultState(this.getStateManager().getDefaultState()\n                .with(FACING, Direction.NORTH)\n                .with(COL, 1)\n                .with(ROW, 0)\n                .with(OPEN, false)\n                .with(POWERED, false));\n    }\n\n    // ---------- допоміжні функції геометрії ----------\n\n    /** Поворот прямокутника (у координатах 0..16) на turns чвертей за годинниковою стрілкою. */\n    private static VoxelShape rotated(double x1, double z1, double x2, double z2, int turns) {\n        for (int i = 0; i < turns; i++) {\n            double nx1 = 16 - z2;\n            double nx2 = 16 - z1;\n            double nz1 = x1;\n            double nz2 = x2;\n            x1 = nx1;\n            x2 = nx2;\n            z1 = nz1;\n            z2 = nz2;\n        }\n        return Block.createCuboidShape(x1, 0, z1, x2, 16, z2);\n    }\n\n    private static int idx(Direction d) {\n        return switch (d) {\n            case EAST -> 1;\n            case SOUTH -> 2;\n            case WEST -> 3;\n            default -> 0;\n        };\n    }\n\n    /** Позиція нижнього середнього блока для частини, що стоїть у pos. */\n    private static BlockPos base(BlockPos pos, BlockState state) {\n        Direction left = state.get(FACING).rotateYCounterclockwise();\n        return pos.down(state.get(ROW)).offset(left, state.get(COL) - 1);\n    }\n\n    /** Позиція частини (c, r) відносно нижнього середнього блока. */\n    private static BlockPos partPos(BlockPos base, Direction facing, int c, int r) {\n        Direction left = facing.rotateYCounterclockwise();\n        return base.offset(left, 1 - c).up(r);\n    }\n\n    // ---------- стани ----------\n\n    @Override\n    protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {\n        builder.add(FACING, COL, ROW, OPEN, POWERED);\n    }\n\n    @Override\n    public BlockState getPlacementState(ItemPlacementContext ctx) {\n        World world = ctx.getWorld();\n        BlockPos origin = ctx.getBlockPos();\n        Direction facing = ctx.getHorizontalPlayerFacing();\n        for (int c = 0; c < 3; c++) {\n            for (int r = 0; r < 3; r++) {\n                BlockPos p = partPos(origin, facing, c, r);\n                if (world.isOutOfHeightLimit(p) || !world.getBlockState(p).canReplace(ctx)) {\n                    return null;\n                }\n            }\n        }\n        return this.getDefaultState().with(FACING, facing).with(COL, 1).with(ROW, 0);\n    }\n\n    @Override\n    public void onPlaced(World world, BlockPos pos, BlockState state, @Nullable LivingEntity placer, ItemStack itemStack) {\n        if (world.isClient()) {\n            return;\n        }\n        Direction facing = state.get(FACING);\n        for (int c = 0; c < 3; c++) {\n            for (int r = 0; r < 3; r++) {\n                if (c == 1 && r == 0) {\n                    continue;\n                }\n                world.setBlockState(partPos(pos, facing, c, r),\n                        this.getDefaultState().with(FACING, facing).with(COL, c).with(ROW, r),\n                        Block.NOTIFY_ALL);\n            }\n        }\n        updatePower(world, pos, state);\n    }\n\n    // ---------- відкривання ----------\n\n    private void setAll(World world, BlockPos base, Direction facing, boolean open, boolean powered) {\n        for (int c = 0; c < 3; c++) {\n            for (int r = 0; r < 3; r++) {\n                BlockPos p = partPos(base, facing, c, r);\n                BlockState s = world.getBlockState(p);\n                if (s.isOf(this) && s.get(FACING) == facing) {\n                    world.setBlockState(p, s.with(OPEN, open).with(POWERED, powered),\n                            Block.NOTIFY_LISTENERS | Block.REDRAW_ON_MAIN_THREAD);\n                }\n            }\n        }\n    }\n\n    private void playToggleSound(World world, BlockPos pos, boolean open) {\n        world.playSound(null, pos, open ? openSound : closeSound, SoundCategory.BLOCKS,\n                1.0f, world.getRandom().nextFloat() * 0.1f + 0.9f);\n    }\n\n    @Override\n    public ActionResult onUse(BlockState state, World world, BlockPos pos, PlayerEntity player, BlockHitResult hit) {\n        if (!handOpen) {\n            return ActionResult.PASS; // залізні двері - тільки редстоун\n        }\n        if (!world.isClient()) {\n            boolean open = !state.get(OPEN);\n            setAll(world, base(pos, state), state.get(FACING), open, state.get(POWERED));\n            playToggleSound(world, pos, open);\n        }\n        return ActionResult.SUCCESS;\n    }\n\n    private void updatePower(World world, BlockPos pos, BlockState state) {\n        Direction facing = state.get(FACING);\n        BlockPos base = base(pos, state);\n        boolean powered = false;\n        for (int c = 0; c < 3 && !powered; c++) {\n            for (int r = 0; r < 3 && !powered; r++) {\n                powered = world.isReceivingRedstonePower(partPos(base, facing, c, r));\n            }\n        }\n        if (powered != state.get(POWERED)) {\n            if (powered != state.get(OPEN)) {\n                playToggleSound(world, pos, powered);\n            }\n            setAll(world, base, facing, powered, powered);\n        }\n    }\n\n    @Override\n    public void neighborUpdate(BlockState state, World world, BlockPos pos, Block sourceBlock,\n                               @Nullable WireOrientation wireOrientation, boolean notify) {\n        if (world.isClient() || sourceBlock == this) {\n            return;\n        }\n        updatePower(world, pos, state);\n    }\n\n    // ---------- ламання ----------\n\n    @Override\n    public BlockState onBreak(World world, BlockPos pos, BlockState state, PlayerEntity player) {\n        if (!world.isClient()) {\n            Direction facing = state.get(FACING);\n            BlockPos base = base(pos, state);\n            for (int c = 0; c < 3; c++) {\n                for (int r = 0; r < 3; r++) {\n                    BlockPos p = partPos(base, facing, c, r);\n                    if (p.equals(pos)) {\n                        continue;\n                    }\n                    BlockState s = world.getBlockState(p);\n                    if (s.isOf(this) && s.get(FACING) == facing) {\n                        world.setBlockState(p, Blocks.AIR.getDefaultState(), Block.NOTIFY_ALL | Block.SKIP_DROPS);\n                    }\n                }\n            }\n            if (!player.isCreative()) {\n                Block.dropStack(world, pos, new ItemStack(this));\n            }\n        }\n        return super.onBreak(world, pos, state, player);\n    }\n\n    // ---------- форми ----------\n\n    @Override\n    public VoxelShape getCollisionShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {\n        int i = idx(state.get(FACING));\n        if (!state.get(OPEN)) {\n            return CLOSED[i];\n        }\n        return switch (state.get(COL)) {\n            case 0 -> LEAF_LEFT[i];\n            case 2 -> LEAF_RIGHT[i];\n            default -> VoxelShapes.empty();\n        };\n    }\n\n    @Override\n    public VoxelShape getOutlineShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {\n        int i = idx(state.get(FACING));\n        if (!state.get(OPEN)) {\n            return CLOSED[i];\n        }\n        return switch (state.get(COL)) {\n            case 0 -> LEAF_LEFT[i];\n            case 2 -> LEAF_RIGHT[i];\n            default -> CLOSED[i]; // щоб у середній (порожній) частині можна було клікнути і закрити\n        };\n    }\n}\n', 'src/main/java/ua/widedoors/WideDoorsMod.java': 'package ua.widedoors;\n\nimport net.fabricmc.api.ModInitializer;\nimport net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;\nimport net.minecraft.block.AbstractBlock;\nimport net.minecraft.block.Block;\nimport net.minecraft.block.piston.PistonBehavior;\nimport net.minecraft.item.BlockItem;\nimport net.minecraft.item.Item;\nimport net.minecraft.item.ItemGroups;\nimport net.minecraft.registry.Registries;\nimport net.minecraft.registry.Registry;\nimport net.minecraft.registry.RegistryKey;\nimport net.minecraft.registry.RegistryKeys;\nimport net.minecraft.sound.BlockSoundGroup;\nimport net.minecraft.sound.SoundEvent;\nimport net.minecraft.sound.SoundEvents;\nimport net.minecraft.util.Identifier;\n\nimport java.util.ArrayList;\nimport java.util.List;\n\npublic class WideDoorsMod implements ModInitializer {\n    public static final String MOD_ID = "widedoors";\n\n    public static final String[] WOODS = {\n            "oak", "spruce", "birch", "jungle", "acacia", "dark_oak",\n            "mangrove", "cherry", "pale_oak", "bamboo", "crimson", "warped"\n    };\n    public static final String[] GLASS_STYLES = {"bars", "grid", "cross"};\n\n    /** Усі двері, крім скляних (для шару рендеру "cutout"). */\n    public static final List<Block> SOLID_BLOCKS = new ArrayList<>();\n    /** Скляні двері (для шару рендеру "translucent"). */\n    public static final List<Block> GLASS_BLOCKS = new ArrayList<>();\n    public static final List<BlockItem> ITEMS = new ArrayList<>();\n\n    private static Block register(String name, AbstractBlock.Settings settings, boolean handOpen,\n                                  SoundEvent open, SoundEvent close) {\n        Identifier id = Identifier.of(MOD_ID, name);\n\n        RegistryKey<Block> blockKey = RegistryKey.of(RegistryKeys.BLOCK, id);\n        WideDoorBlock block = new WideDoorBlock(settings.registryKey(blockKey), handOpen, open, close);\n        Registry.register(Registries.BLOCK, blockKey, block);\n\n        RegistryKey<Item> itemKey = RegistryKey.of(RegistryKeys.ITEM, id);\n        BlockItem item = new BlockItem(block, new Item.Settings().registryKey(itemKey).useBlockPrefixedTranslationKey());\n        Registry.register(Registries.ITEM, itemKey, item);\n        ITEMS.add(item);\n\n        return block;\n    }\n\n    private static AbstractBlock.Settings woodSettings() {\n        return AbstractBlock.Settings.create()\n                .strength(3.0f)\n                .sounds(BlockSoundGroup.WOOD)\n                .nonOpaque()\n                .pistonBehavior(PistonBehavior.BLOCK);\n    }\n\n    @Override\n    public void onInitialize() {\n        for (String wood : WOODS) {\n            SOLID_BLOCKS.add(register("wide_" + wood + "_door", woodSettings(), true,\n                    SoundEvents.BLOCK_WOODEN_DOOR_OPEN, SoundEvents.BLOCK_WOODEN_DOOR_CLOSE));\n            for (String style : GLASS_STYLES) {\n                GLASS_BLOCKS.add(register("wide_" + wood + "_glass_door_" + style, woodSettings(), true,\n                        SoundEvents.BLOCK_WOODEN_DOOR_OPEN, SoundEvents.BLOCK_WOODEN_DOOR_CLOSE));\n            }\n        }\n\n        SOLID_BLOCKS.add(register("wide_iron_door",\n                AbstractBlock.Settings.create()\n                        .strength(5.0f)\n                        .sounds(BlockSoundGroup.METAL)\n                        .nonOpaque()\n                        .pistonBehavior(PistonBehavior.BLOCK),\n                false, SoundEvents.BLOCK_IRON_DOOR_OPEN, SoundEvents.BLOCK_IRON_DOOR_CLOSE));\n\n        ItemGroupEvents.modifyEntriesEvent(ItemGroups.REDSTONE).register(entries -> {\n            for (BlockItem item : ITEMS) {\n                entries.add(item);\n            }\n        });\n    }\n}\n', 'src/main/java/ua/widedoors/WideDoorsClient.java': 'package ua.widedoors;\n\nimport net.fabricmc.api.ClientModInitializer;\nimport net.minecraft.block.Block;\n\nimport java.lang.reflect.Method;\nimport java.lang.reflect.Modifier;\n\n/**\n * Вмикає прозорість: скляні двері - translucent, решта - cutout.\n * Через рефлексію, щоб не залежати від точної назви класу в різних версіях Fabric API.\n */\npublic class WideDoorsClient implements ClientModInitializer {\n    @Override\n    public void onInitializeClient() {\n        for (Block b : WideDoorsMod.SOLID_BLOCKS) {\n            setLayer(b, "CUTOUT");\n        }\n        for (Block b : WideDoorsMod.GLASS_BLOCKS) {\n            setLayer(b, "TRANSLUCENT");\n        }\n    }\n\n    private static void setLayer(Block block, String layerName) {\n        String[] classNames = {\n                "net.fabricmc.fabric.api.client.rendering.v1.BlockRenderLayerMap",\n                "net.fabricmc.fabric.api.blockrenderlayer.v1.BlockRenderLayerMap"\n        };\n        for (String className : classNames) {\n            try {\n                Class<?> cls = Class.forName(className);\n                Object instance = null;\n                try {\n                    instance = cls.getField("INSTANCE").get(null);\n                } catch (Throwable ignored) {\n                }\n                for (Method m : cls.getMethods()) {\n                    if (!m.getName().equals("putBlock") || m.getParameterCount() != 2) continue;\n                    Class<?> layerType = m.getParameterTypes()[1];\n                    if (!layerType.isEnum() || !m.getParameterTypes()[0].isAssignableFrom(Block.class)) continue;\n                    Object constant = null;\n                    for (Object o : layerType.getEnumConstants()) {\n                        if (((Enum<?>) o).name().equals(layerName)) constant = o;\n                    }\n                    if (constant == null) continue;\n                    m.invoke(Modifier.isStatic(m.getModifiers()) ? null : instance, block, constant);\n                    return;\n                }\n            } catch (Throwable ignored) {\n            }\n        }\n        System.err.println("[widedoors] Could not set render layer for " + block);\n    }\n}\n', 'src/main/resources/fabric.mod.json': '{\n  "schemaVersion": 1,\n  "id": "widedoors",\n  "version": "${version}",\n  "name": "Wide Doors",\n  "description": "Великі двері 3x3 з двома стулками, що відкриваються. Усі види дерева, суцільні й скляні.",\n  "authors": [],\n  "license": "MIT",\n  "icon": "assets/widedoors/icon.png",\n  "environment": "*",\n  "entrypoints": {\n    "main": ["ua.widedoors.WideDoorsMod"],\n    "client": ["ua.widedoors.WideDoorsClient"]\n  },\n  "depends": {\n    "fabricloader": ">=0.18.1",\n    "minecraft": "~1.21.11",\n    "java": ">=21",\n    "fabric-api": "*"\n  }\n}\n'}
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
        json.dump(obj, f, indent=1, ensure_ascii=False)

# id, укр. назва, англ. назва, текстура кори, приблизний колір (тільки для іконок)
WOODS = [
    ("oak", "дуб", "Oak", "oak_log", (162, 130, 78)),
    ("spruce", "ялина", "Spruce", "spruce_log", (114, 84, 48)),
    ("birch", "береза", "Birch", "birch_log", (192, 175, 121)),
    ("jungle", "тропічне дерево", "Jungle", "jungle_log", (160, 115, 80)),
    ("acacia", "акація", "Acacia", "acacia_log", (168, 90, 50)),
    ("dark_oak", "темний дуб", "Dark Oak", "dark_oak_log", (66, 43, 20)),
    ("mangrove", "мангрове дерево", "Mangrove", "mangrove_log", (117, 54, 48)),
    ("cherry", "вишня", "Cherry", "cherry_log", (226, 178, 172)),
    ("pale_oak", "блідий дуб", "Pale Oak", "pale_oak_log", (227, 213, 205)),
    ("bamboo", "бамбук", "Bamboo", "bamboo_block", (193, 173, 80)),
    ("crimson", "багряне дерево", "Crimson", "crimson_stem", (101, 48, 70)),
    ("warped", "викривлене дерево", "Warped", "warped_stem", (43, 104, 99)),
]
STYLES = [("bars", "перемички", "Bars"), ("grid", "решітка", "Grid"), ("cross", "хрест", "Cross")]

# ---------- розмітка однієї стулки (s = відстань від петель 0..24, y = висота 0..48 пікселів) ----------
def leaf_rects(style):
    if style == "door":
        return [("dbot", 0, 24, 0, 24), ("dtop", 0, 24, 24, 48)]
    r = [("frame", 0, 24, 0, 3), ("frame", 0, 24, 45, 48), ("frame", 0, 3, 3, 45), ("frame", 21, 24, 3, 45)]
    rows3 = ((3, 15), (17, 31), (33, 45))
    rows2 = ((3, 23), (25, 45))
    cols2 = ((3, 11), (13, 21))
    if style == "bars":
        r += [("bar", 3, 21, 15, 17), ("bar", 3, 21, 31, 33)]
        panes = [(3, 21, y1, y2) for (y1, y2) in rows3]
    elif style == "grid":
        r += [("bar", 3, 21, 15, 17), ("bar", 3, 21, 31, 33)]
        r += [("bar", 11, 13, y1, y2) for (y1, y2) in rows3]
        panes = [(a, b, y1, y2) for (y1, y2) in rows3 for (a, b) in cols2]
    else:  # cross
        r += [("bar", 3, 21, 23, 25)]
        r += [("bar", 11, 13, y1, y2) for (y1, y2) in rows2]
        panes = [(a, b, y1, y2) for (y1, y2) in rows2 for (a, b) in cols2]
    r += [("glass",) + p for p in panes]
    return r

def uv_funcs(rect):
    kind, s1, s2, y1, y2 = rect
    if kind == "dbot":
        return (lambda s: s/24*16), (lambda y: (24-y)/24*16)
    if kind == "dtop":
        return (lambda s: s/24*16), (lambda y: (48-y)/24*16)
    if kind == "glass":
        return (lambda s: (s-s1)/(s2-s1)*16), (lambda y: (y2-y)/(y2-y1)*16)
    return None, None

TEX = {"frame": "#frame", "bar": "#bar", "glass": "#glass", "dbot": "#dbot", "dtop": "#dtop"}
EXPLICIT = ("glass", "dbot", "dtop")

def r4(v): return round(v, 4)

def closed_depth(kind):
    if kind in ("frame", "dbot", "dtop"): return 13, 16
    if kind == "bar": return 14, 15
    return 14.5, 15.5

def open_depth(kind, side):
    if side == "left":
        return {"frame": (0, 3), "dbot": (0, 3), "dtop": (0, 3), "bar": (1, 2), "glass": (1.25, 1.75)}[kind]
    return {"frame": (13, 16), "dbot": (13, 16), "dtop": (13, 16), "bar": (14, 15), "glass": (14.25, 14.75)}[kind]

def closed_elements(c, r, style):
    els = []
    for leaf in ("L", "R"):
        for rect in leaf_rects(style):
            kind, s1, s2, y1, y2 = rect
            X1, X2 = (s1, s2) if leaf == "L" else (48 - s2, 48 - s1)
            cx1, cx2 = max(X1, 16*c), min(X2, 16*c + 16)
            cy1, cy2 = max(y1, 16*r), min(y2, 16*r + 16)
            if cx1 >= cx2 or cy1 >= cy2: continue
            sa, sb = (cx1, cx2) if leaf == "L" else (48 - cx2, 48 - cx1)
            lx1, lx2, ly1, ly2 = cx1 - 16*c, cx2 - 16*c, cy1 - 16*r, cy2 - 16*r
            z1, z2 = closed_depth(kind)
            tex = TEX[kind]
            faces = {}
            horiz = (s2 - s1) > (y2 - y1) and kind == "frame"
            for fn in ("south", "north"):
                f = {"texture": tex}
                if kind in EXPLICIT:
                    uf, vf = uv_funcs(rect)
                    ua, ub, vt, vb = uf(sa), uf(sb), vf(cy2), vf(cy1)
                    lo_left = (leaf == "L")  # south: ліворуч менше X
                    if fn == "north": lo_left = not lo_left
                    f["uv"] = [r4(ua), r4(vt), r4(ub), r4(vb)] if lo_left else [r4(ub), r4(vt), r4(ua), r4(vb)]
                elif horiz:
                    f["rotation"] = 90
                faces[fn] = f
            if kind != "glass":
                for fn in ("east", "west", "up", "down"):
                    faces[fn] = {"texture": tex}
            els.append({"from": [r4(lx1), r4(ly1), z1], "to": [r4(lx2), r4(ly2), z2], "faces": faces})
    return els

def open_elements(side, r, style):
    els = []
    for rect in leaf_rects(style):
        kind, s1, s2, y1, y2 = rect
        sa, sb = max(s1, 0), min(s2, 16)
        cy1, cy2 = max(y1, 16*r), min(y2, 16*r + 16)
        if sa >= sb or cy1 >= cy2: continue
        ly1, ly2 = cy1 - 16*r, cy2 - 16*r
        x1, x2 = open_depth(kind, side)
        z1, z2 = 16 - sb, 16 - sa
        tex = TEX[kind]
        horiz = (s2 - s1) > (y2 - y1) and kind == "frame"
        faces = {}
        for fn in ("east", "west"):
            f = {"texture": tex}
            if kind in EXPLICIT:
                uf, vf = uv_funcs(rect)
                ua, ub, vt, vb = uf(sa), uf(sb), vf(cy2), vf(cy1)
                f["uv"] = [r4(ua), r4(vt), r4(ub), r4(vb)] if fn == "east" else [r4(ub), r4(vt), r4(ua), r4(vb)]
            elif horiz:
                f["rotation"] = 90
            faces[fn] = f
        if kind != "glass":
            for fn in ("north", "south", "up", "down"):
                faces[fn] = {"texture": tex}
        els.append({"from": [x1, r4(ly1), r4(z1)], "to": [x2, r4(ly2), r4(z2)], "faces": faces})
    return els

ROT = {"north": 0, "east": 90, "south": 180, "west": 270}

def write_door(name, style, textures):
    for c in range(3):
        for r in range(3):
            w(f"{A}/models/block/{name}_c{c}r{r}.json", {"textures": textures, "elements": closed_elements(c, r, style)})
    for r in range(3):
        w(f"{A}/models/block/{name}_open_left_r{r}.json", {"textures": textures, "elements": open_elements("left", r, style)})
        w(f"{A}/models/block/{name}_open_right_r{r}.json", {"textures": textures, "elements": open_elements("right", r, style)})
    variants = {}
    for d, y in ROT.items():
        for c in range(3):
            for r in range(3):
                for o in ("false", "true"):
                    if o == "false": m = f"widedoors:block/{name}_c{c}r{r}"
                    elif c == 0: m = f"widedoors:block/{name}_open_left_r{r}"
                    elif c == 2: m = f"widedoors:block/{name}_open_right_r{r}"
                    else: m = "widedoors:block/empty"
                    variants[f"col={c},facing={d},open={o},row={r}"] = {"model": m, "y": y}
    w(f"{A}/blockstates/{name}.json", {"variants": variants})

def write_item(name, layer0):
    w(f"{A}/items/{name}.json", {"model": {"type": "minecraft:model", "model": f"widedoors:item/{name}"}})
    w(f"{A}/models/item/{name}.json", {"parent": "minecraft:item/generated", "textures": {"layer0": layer0}})

def make_icon(path, color, style):
    rnd = random.Random(1)
    img = Image.new("RGBA", (48, 48), (0, 0, 0, 0)); px = img.load()
    for leaf in ("L", "R"):
        for kind, s1, s2, y1, y2 in leaf_rects(style):
            X1, X2 = (s1, s2) if leaf == "L" else (48 - s2, 48 - s1)
            for X in range(X1, X2):
                for Y in range(y1, y2):
                    yy = 47 - Y
                    if kind == "glass": px[X, yy] = (200, 230, 240, 120)
                    else:
                        v = tuple(max(0, min(255, k + rnd.randint(-8, 8))) for k in color)
                        if kind == "bar": v = tuple(min(255, k + 12) for k in v)
                        px[X, yy] = v + (255,)
    img.resize((16, 16), Image.BOX).save(path)

# ---------- порожня модель, іконка мода ----------
w(f"{A}/models/block/empty.json", {"textures": {"particle": "minecraft:block/oak_planks"}, "elements": []})
os.makedirs(f"{A}/textures/item", exist_ok=True)
ic = Image.new("RGBA", (16, 16)); make_icon(f"{A}/textures/item/_tmp.png", WOODS[0][4], "grid")
Image.open(f"{A}/textures/item/_tmp.png").resize((64, 64), Image.NEAREST).save(f"{A}/icon.png")
os.remove(f"{A}/textures/item/_tmp.png")

en, uk = {}, {}
axe, pick = [], []

for wid, ukn, enn, log, col in WOODS:
    planks = f"minecraft:block/{wid}_planks"
    base_tex = {"particle": planks, "frame": f"minecraft:block/{log}", "bar": planks,
                "glass": "minecraft:block/glass",
                "dtop": f"minecraft:block/{wid}_door_top", "dbot": f"minecraft:block/{wid}_door_bottom"}
    # суцільні двері
    name = f"wide_{wid}_door"
    write_door(name, "door", base_tex)
    write_item(name, f"minecraft:item/{wid}_door")
    en[f"block.widedoors.{name}"] = f"Wide {enn} Door"
    uk[f"block.widedoors.{name}"] = f"Широкі двері ({ukn})"
    axe.append(f"widedoors:{name}")
    w(f"{D}/widedoors/recipe/{name}.json", {
        "type": "minecraft:crafting_shaped", "category": "redstone",
        "key": {"P": f"minecraft:{wid}_planks", "D": f"minecraft:{wid}_door"},
        "pattern": ["PPP", "PDP", "PDP"], "result": {"id": f"widedoors:{name}", "count": 1}})
    # скляні двері
    for sid, sukn, sen in STYLES:
        gname = f"wide_{wid}_glass_door_{sid}"
        write_door(gname, sid, base_tex)
        make_icon(f"{A}/textures/item/{gname}.png", col, sid)
        write_item(gname, f"widedoors:item/{gname}")
        en[f"block.widedoors.{gname}"] = f"Wide {enn} Glass Door ({sen})"
        uk[f"block.widedoors.{gname}"] = f"Широкі скляні двері ({ukn}, {sukn})"
        axe.append(f"widedoors:{gname}")
        extra = {"bars": [], "grid": ["minecraft:stick", "minecraft:stick"], "cross": ["minecraft:stick"]}[sid]
        w(f"{D}/widedoors/recipe/{gname}.json", {
            "type": "minecraft:crafting_shapeless", "category": "redstone",
            "ingredients": [f"widedoors:{name}"] + ["minecraft:glass"]*4 + extra,
            "result": {"id": f"widedoors:{gname}", "count": 1}})

# залізні двері
write_door("wide_iron_door", "door", {"particle": "minecraft:block/iron_block",
           "dtop": "minecraft:block/iron_door_top", "dbot": "minecraft:block/iron_door_bottom"})
write_item("wide_iron_door", "minecraft:item/iron_door")
en["block.widedoors.wide_iron_door"] = "Wide Iron Door"
uk["block.widedoors.wide_iron_door"] = "Широкі залізні двері"
pick.append("widedoors:wide_iron_door")
w(f"{D}/widedoors/recipe/wide_iron_door.json", {
    "type": "minecraft:crafting_shaped", "category": "redstone",
    "key": {"P": "minecraft:iron_ingot", "D": "minecraft:iron_door"},
    "pattern": ["PPP", "PDP", "PDP"], "result": {"id": "widedoors:wide_iron_door", "count": 1}})

w(f"{A}/lang/en_us.json", en)
w(f"{A}/lang/uk_ua.json", uk)
w(f"{D}/minecraft/tags/block/mineable/axe.json", {"replace": False, "values": axe})
w(f"{D}/minecraft/tags/block/mineable/pickaxe.json", {"replace": False, "values": pick})
print("done")
