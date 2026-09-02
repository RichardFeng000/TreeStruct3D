# Runtime Anchor Audit — benchmark

- Blender: 5.0.0
- Progress: 212/212
- Success: 204
- Errors: 8
- Single final Mesh with no runtime relations: 194
- Models with confirmed shared anchors: 4
- Models with broken/misaligned anchors: 6

| Seed | Status | Nodes | Edges | Directed | Shared | Broken | Seconds | Problem |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| AgaveMonocot_seed0 | error | - | - | - | - | - | 60.018 | timeout |
  - `AgaveMonocot_seed0`: Command '['/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--python', '/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/part_causal_graph_v0/part_causal_graph/blender_probe.py', '--', '--script', 'visual_validation/datasets/benchmark/categories/AgaveMonocot_seed0/AgaveMonocot_seed0.py', '--source-root', 'visual_validation/datasets/benchmark/categories/AgaveMonocot_seed0', '--output', 'visual_validation/.model_playground_cache/.AgaveMonocot_seed0-runtime-graph-8c77e60fadc3e7a4ee43.raw.json', '--contact-ratio', '0.025', '--anchor-ratio', '0.025', '--max-nodes', '128', '--max-edges', '512', '--samples', '96']' timed out after 60 seconds
| AquariumTank_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 11.510 | single_final_mesh_no_runtime_relations |
| ArmChair_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 6.760 | single_final_mesh_no_runtime_relations |
| Auger_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 6.942 | single_final_mesh_no_runtime_relations |
| Balloon_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 24.248 | single_final_mesh_no_runtime_relations |
| BananaMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 10.400 | single_final_mesh_no_runtime_relations |
| BasketBase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 33.153 | single_final_mesh_no_runtime_relations |
| BathroomSink_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.164 | single_final_mesh_no_runtime_relations |
| Bathtub_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.900 | single_final_mesh_no_runtime_relations |
| Bed_seed0 | ok | 6 | 12 | 5 | 0 | 7 | 33.079 |  |
| BedFrame_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.127 | single_final_mesh_no_runtime_relations |
| Beetle_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.253 | single_final_mesh_no_runtime_relations |
| BeverageFridge_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.974 | single_final_mesh_no_runtime_relations |
| Bird_seed0 | ok | 12 | 23 | 11 | 9 | 8 | 0.000 |  |
| Blanket_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.693 | single_final_mesh_no_runtime_relations |
| BlenderRock_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.937 | single_final_mesh_no_runtime_relations |
| Book_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.563 | single_final_mesh_no_runtime_relations |
| BookColumn_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.621 | single_final_mesh_no_runtime_relations |
| BookStack_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.584 | single_final_mesh_no_runtime_relations |
| Bottle_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 5.696 | single_final_mesh_no_runtime_relations |
| Boulder_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 15.985 | single_final_mesh_no_runtime_relations |
| BoulderPile_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 18.488 | single_final_mesh_no_runtime_relations |
| Bowl_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.550 | single_final_mesh_no_runtime_relations |
| BoxComforter_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.807 | single_final_mesh_no_runtime_relations |
| BrainCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 22.804 | single_final_mesh_no_runtime_relations |
| Branch_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.125 | single_final_mesh_no_runtime_relations |
| Bush_seed0 | error | - | - | - | - | - | 60.014 | timeout |
  - `Bush_seed0`: Command '['/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--python', '/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/part_causal_graph_v0/part_causal_graph/blender_probe.py', '--', '--script', 'visual_validation/datasets/benchmark/categories/Bush_seed0/Bush_seed0.py', '--source-root', 'visual_validation/datasets/benchmark/categories/Bush_seed0', '--output', 'visual_validation/.model_playground_cache/.Bush_seed0-runtime-graph-37c9f92a8f9d339da65e.raw.json', '--contact-ratio', '0.025', '--anchor-ratio', '0.025', '--max-nodes', '128', '--max-edges', '512', '--samples', '96']' timed out after 60 seconds
| BushCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 51.869 | single_final_mesh_no_runtime_relations |
| Cabinet_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.736 | single_final_mesh_no_runtime_relations |
| CabinetDoorBase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.497 | single_final_mesh_no_runtime_relations |
| CabinetDoorIkea_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.582 | single_final_mesh_no_runtime_relations |
| CabinetDrawerBase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.617 | single_final_mesh_no_runtime_relations |
| Can_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.644 | single_final_mesh_no_runtime_relations |
| CantileverStaircase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.839 | single_final_mesh_no_runtime_relations |
| Carnivore_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 11.355 | single_final_mesh_no_runtime_relations |
| CauliflowerCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 31.730 | single_final_mesh_no_runtime_relations |
| CeilingClassicLamp_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.536 | single_final_mesh_no_runtime_relations |
| CeilingLight_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.780 | single_final_mesh_no_runtime_relations |
| CellShelf_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.640 | single_final_mesh_no_runtime_relations |
| Chameleon_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 6.772 | single_final_mesh_no_runtime_relations |
| Chopsticks_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.052 | single_final_mesh_no_runtime_relations |
| Clam_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 9.520 | single_final_mesh_no_runtime_relations |
| CoconutTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.713 | single_final_mesh_no_runtime_relations |
| CoffeeTable_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.577 | single_final_mesh_no_runtime_relations |
| ColumnarBaseCactus_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.359 | single_final_mesh_no_runtime_relations |
| ColumnarCactus_seed0 | error | - | - | - | - | - | 60.018 | timeout |
  - `ColumnarCactus_seed0`: Command '['/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--python', '/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/part_causal_graph_v0/part_causal_graph/blender_probe.py', '--', '--script', 'visual_validation/datasets/benchmark/categories/ColumnarCactus_seed0/ColumnarCactus_seed0.py', '--source-root', 'visual_validation/datasets/benchmark/categories/ColumnarCactus_seed0', '--output', 'visual_validation/.model_playground_cache/.ColumnarCactus_seed0-runtime-graph-731ca61a057635c20133.raw.json', '--contact-ratio', '0.025', '--anchor-ratio', '0.025', '--max-nodes', '128', '--max-edges', '512', '--samples', '96']' timed out after 60 seconds
| Comforter_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.860 | single_final_mesh_no_runtime_relations |
| Conch_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 5.702 | single_final_mesh_no_runtime_relations |
| Countertop_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.685 | single_final_mesh_no_runtime_relations |
| Crab_seed0 | ok | 13 | 16 | 12 | 10 | 6 | 11.064 |  |
| Cup_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 8.438 | single_final_mesh_no_runtime_relations |
| CurvedStaircase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 5.276 | single_final_mesh_no_runtime_relations |
| Dandelion_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 28.425 | single_final_mesh_no_runtime_relations |
| DandelionSeed_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.078 | single_final_mesh_no_runtime_relations |
| DeskLamp_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.270 | single_final_mesh_no_runtime_relations |
| DiffGrowthBaseCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.451 | single_final_mesh_no_runtime_relations |
| Dishwasher_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.130 | single_final_mesh_no_runtime_relations |
| DoorCasing_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.570 | single_final_mesh_no_runtime_relations |
| Dragonfly_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 8.694 | single_final_mesh_no_runtime_relations |
| ElkhornCoral_seed0 | error | - | - | - | - | - | 1.832 | no_observable_geometry |
  - `ElkhornCoral_seed0`: RuntimeError: script produced no observable geometry nodes Traceback (most recent call last): File "/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/part_causal_graph_v0/part_causal_graph/blender_probe.py", line 916, in main raise RuntimeError("script produced no observable geometry nodes") RuntimeError: script produced no observable geometry nodes
| FallenTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 12.487 | single_final_mesh_no_runtime_relations |
| FanCoral_seed0 | error | - | - | - | - | - | 1.031 | runtime_error |
  - `FanCoral_seed0`: ValueError: all index and data arrays must have the same length Traceback (most recent call last): File "/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/part_causal_graph_v0/part_causal_graph/blender_probe.py", line 845, in main exec(code, namespace) File "visual_validation/datasets/benchmark/categories/FanCoral_seed0/FanCoral_seed0.py", line 168, in <module> ext_graph = csr_matrix((ext_data, (ext_row, ext_col)), shape=(n_total, n_total)) ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ File "/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/Resources/5.0/python/lib/python3.11/site-packages/scipy/sparse/_compressed.py", line 57, in __init__ coo = self._coo_container(arg1, shape=shape, dtype=dtype) ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ File "/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/Resources/5.0/python/lib/python3.11/site-packages/scipy/sparse/_coo.py", line 103, in __init__ self._check() File "/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/Resources/5.0/python/lib/python3.11/site-packages/scipy/sparse/_coo.py", line 221, in _check if self.nnz > 0: ^^^^^^^^ File "/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/Resources/5.0/python/lib/python3.11/site-packages/scipy/sparse/_base.py", line 373, in nnz return self._getnnz() ^^^^^^^^^^^^^^ File "/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/Resources/5.0/python/lib/python3.11/site-packages/scipy/sparse/_coo.py", line 171, in _getnnz raise ValueError('all index and data arrays must have the ' ValueError: all index and data arrays must have the same length
| Fern_seed0 | error | - | - | - | - | - | 60.021 | timeout |
  - `Fern_seed0`: Command '['/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--python', '/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/part_causal_graph_v0/part_causal_graph/blender_probe.py', '--', '--script', 'visual_validation/datasets/benchmark/categories/Fern_seed0/Fern_seed0.py', '--source-root', 'visual_validation/datasets/benchmark/categories/Fern_seed0', '--output', 'visual_validation/.model_playground_cache/.Fern_seed0-runtime-graph-74d22578951e5a55280b.raw.json', '--contact-ratio', '0.025', '--anchor-ratio', '0.025', '--max-nodes', '128', '--max-edges', '512', '--samples', '96']' timed out after 60 seconds
| Fish_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 7.361 | single_final_mesh_no_runtime_relations |
| FloorLamp_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.237 | single_final_mesh_no_runtime_relations |
| Flower_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.436 | single_final_mesh_no_runtime_relations |
| FlowerPlant_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.851 | single_final_mesh_no_runtime_relations |
| FlyingBird_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 6.501 | single_final_mesh_no_runtime_relations |
| FoodBag_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.497 | single_final_mesh_no_runtime_relations |
| FoodBox_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.556 | single_final_mesh_no_runtime_relations |
| Fork_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.666 | single_final_mesh_no_runtime_relations |
| FruitApple_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.700 | single_final_mesh_no_runtime_relations |
| FruitBlackberry_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 8.000 | single_final_mesh_no_runtime_relations |
| FruitCoconutgreen_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.694 | single_final_mesh_no_runtime_relations |
| FruitCoconuthairy_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 14.655 | single_final_mesh_no_runtime_relations |
| FruitContainer_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.730 | single_final_mesh_no_runtime_relations |
| FruitDurian_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 17.127 | single_final_mesh_no_runtime_relations |
| FruitPineapple_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 10.043 | single_final_mesh_no_runtime_relations |
| FruitStarfruit_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.944 | single_final_mesh_no_runtime_relations |
| FruitStrawberry_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 7.947 | single_final_mesh_no_runtime_relations |
| GlobularBaseCactus_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.698 | single_final_mesh_no_runtime_relations |
| GlobularCactus_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 32.293 | single_final_mesh_no_runtime_relations |
| GlowingRocks_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 10.013 | single_final_mesh_no_runtime_relations |
| GrassesMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.549 | single_final_mesh_no_runtime_relations |
| GrassTuft_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.828 | single_final_mesh_no_runtime_relations |
| Hardware_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.562 | single_final_mesh_no_runtime_relations |
| Herbivore_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.558 | single_final_mesh_no_runtime_relations |
| HollowTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 17.761 | single_final_mesh_no_runtime_relations |
| HoneycombCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 22.761 | single_final_mesh_no_runtime_relations |
| HookBase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.615 | single_final_mesh_no_runtime_relations |
| Jar_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 24.415 | single_final_mesh_no_runtime_relations |
| Jellyfish_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 22.538 | single_final_mesh_no_runtime_relations |
| KelpMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 57.535 | single_final_mesh_no_runtime_relations |
| KitchenCabinet_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.746 | single_final_mesh_no_runtime_relations |
| KitchenIsland_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.641 | single_final_mesh_no_runtime_relations |
| KitchenSpace_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.637 | single_final_mesh_no_runtime_relations |
| Knife_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.653 | single_final_mesh_no_runtime_relations |
| LargePlantContainer_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 21.881 | single_final_mesh_no_runtime_relations |
| LargeShelf_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.613 | single_final_mesh_no_runtime_relations |
| Leaf_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.557 | single_final_mesh_no_runtime_relations |
| LeafBananaTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.208 | single_final_mesh_no_runtime_relations |
| LeafBroadleaf_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 8.153 | single_final_mesh_no_runtime_relations |
| LeafGinko_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.343 | single_final_mesh_no_runtime_relations |
| LeafHeart_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.555 | single_final_mesh_no_runtime_relations |
| LeafMaple_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 19.150 | single_final_mesh_no_runtime_relations |
| LeafPalmPlant_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.719 | single_final_mesh_no_runtime_relations |
| LeafPalmTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 7.731 | single_final_mesh_no_runtime_relations |
| LeafPine_seed0 | ok | 2 | 1 | 0 | 0 | 0 | 0.710 |  |
| LeafV2_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 6.443 | single_final_mesh_no_runtime_relations |
| LeatherCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 16.402 | single_final_mesh_no_runtime_relations |
| Lichen_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.228 | single_final_mesh_no_runtime_relations |
| Lid_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.752 | single_final_mesh_no_runtime_relations |
| LiteDoor_seed0 | ok | 3 | 0 | 0 | 0 | 0 | 0.646 |  |
| Lobster_seed0 | ok | 15 | 26 | 14 | 12 | 6 | 11.452 |  |
| LouverDoor_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.702 | single_final_mesh_no_runtime_relations |
| LShapedStaircase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.147 | single_final_mesh_no_runtime_relations |
| MaizeMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.073 | single_final_mesh_no_runtime_relations |
| Mattress_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.450 | single_final_mesh_no_runtime_relations |
| Microwave_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.931 | single_final_mesh_no_runtime_relations |
| Mirror_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.550 | single_final_mesh_no_runtime_relations |
| Monitor_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.709 | single_final_mesh_no_runtime_relations |
| Moss_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.559 | single_final_mesh_no_runtime_relations |
| Mushroom_seed0 | error | - | - | - | - | - | 60.024 | timeout |
  - `Mushroom_seed0`: Command '['/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--python', '/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/part_causal_graph_v0/part_causal_graph/blender_probe.py', '--', '--script', 'visual_validation/datasets/benchmark/categories/Mushroom_seed0/Mushroom_seed0.py', '--source-root', 'visual_validation/datasets/benchmark/categories/Mushroom_seed0', '--output', 'visual_validation/.model_playground_cache/.Mushroom_seed0-runtime-graph-697ec9d365df8fb83c2a.raw.json', '--contact-ratio', '0.025', '--anchor-ratio', '0.025', '--max-nodes', '128', '--max-edges', '512', '--samples', '96']' timed out after 60 seconds
| MushroomCap_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.640 | single_final_mesh_no_runtime_relations |
| MushroomGrowth_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 40.850 | single_final_mesh_no_runtime_relations |
| MushroomStem_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.979 | single_final_mesh_no_runtime_relations |
| Mussel_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 9.480 | single_final_mesh_no_runtime_relations |
| NatureShelfTrinkets_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.632 | single_final_mesh_no_runtime_relations |
| Nautilus_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.105 | single_final_mesh_no_runtime_relations |
| NumLeafGrass_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.594 | single_final_mesh_no_runtime_relations |
| Oven_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 5.812 | single_final_mesh_no_runtime_relations |
| Pallet_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.573 | single_final_mesh_no_runtime_relations |
| PalmTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 29.190 | single_final_mesh_no_runtime_relations |
| Pan_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.528 | single_final_mesh_no_runtime_relations |
| PanelDoor_seed0 | ok | 3 | 0 | 0 | 0 | 0 | 0.713 |  |
| Pants_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.245 | single_final_mesh_no_runtime_relations |
| Pillar_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.413 | single_final_mesh_no_runtime_relations |
| Pillow_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.610 | single_final_mesh_no_runtime_relations |
| Pinecone_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.000 | single_final_mesh_no_runtime_relations |
| PineNeedle_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.557 | single_final_mesh_no_runtime_relations |
| PlantBananaTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.907 | single_final_mesh_no_runtime_relations |
| PlantContainer_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 22.287 | single_final_mesh_no_runtime_relations |
| PlantPot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.192 | single_final_mesh_no_runtime_relations |
| Plate_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.573 | single_final_mesh_no_runtime_relations |
| PlateBase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.590 | single_final_mesh_no_runtime_relations |
| PlateOnRackBase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.650 | single_final_mesh_no_runtime_relations |
| PlateRackBase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.632 | single_final_mesh_no_runtime_relations |
| Pot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 12.938 | single_final_mesh_no_runtime_relations |
| PrickyPearBaseCactus_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.018 | single_final_mesh_no_runtime_relations |
| PrickyPearCactus_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 16.416 | single_final_mesh_no_runtime_relations |
| Rack_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.057 | single_final_mesh_no_runtime_relations |
| Raindrop_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.684 | single_final_mesh_no_runtime_relations |
| RangeHood_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.830 | single_final_mesh_no_runtime_relations |
| ReactionDiffusionBaseCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 17.990 | single_final_mesh_no_runtime_relations |
| ReedBranchMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 9.421 | single_final_mesh_no_runtime_relations |
| ReedEarMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.793 | single_final_mesh_no_runtime_relations |
| ReedMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 11.284 | single_final_mesh_no_runtime_relations |
| RottenTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 21.296 | single_final_mesh_no_runtime_relations |
| Rug_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.574 | single_final_mesh_no_runtime_relations |
| Scallop_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 9.329 | single_final_mesh_no_runtime_relations |
| Seaweed_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 5.402 | single_final_mesh_no_runtime_relations |
| Shirt_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.626 | single_final_mesh_no_runtime_relations |
| SideTable_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.684 | single_final_mesh_no_runtime_relations |
| SidetableDesk_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.636 | single_final_mesh_no_runtime_relations |
| SimpleBookcase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.577 | single_final_mesh_no_runtime_relations |
| SimpleDesk_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.633 | single_final_mesh_no_runtime_relations |
| SingleCabinet_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.733 | single_final_mesh_no_runtime_relations |
| Sink_seed0 | ok | 2 | 1 | 1 | 0 | 1 | 1.899 |  |
| Snake_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.835 | single_final_mesh_no_runtime_relations |
| SnakePlant_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.748 | single_final_mesh_no_runtime_relations |
| Sofa_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 5.341 | single_final_mesh_no_runtime_relations |
| Spatula_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.651 | single_final_mesh_no_runtime_relations |
| SpatulaBase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.685 | single_final_mesh_no_runtime_relations |
| SpatulaOnHookBase_seed0 | ok | 2 | 1 | 0 | 0 | 0 | 0.756 |  |
| SpiderPlant_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.681 | single_final_mesh_no_runtime_relations |
| SpinyLobster_seed0 | ok | 15 | 27 | 14 | 14 | 2 | 5.743 |  |
| SpiralStaircase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.717 | single_final_mesh_no_runtime_relations |
| Spoon_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.692 | single_final_mesh_no_runtime_relations |
| StandingSink_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.727 | single_final_mesh_no_runtime_relations |
| StarCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 12.765 | single_final_mesh_no_runtime_relations |
| StraightStaircase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.651 | single_final_mesh_no_runtime_relations |
| Succulent_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 40.544 | single_final_mesh_no_runtime_relations |
| TableCocktail_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.457 | single_final_mesh_no_runtime_relations |
| TableCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.643 | single_final_mesh_no_runtime_relations |
| TableDining_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.658 | single_final_mesh_no_runtime_relations |
| Tap_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.858 | single_final_mesh_no_runtime_relations |
| TaroMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 8.042 | single_final_mesh_no_runtime_relations |
| Toilet_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.187 | single_final_mesh_no_runtime_relations |
| Towel_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.454 | single_final_mesh_no_runtime_relations |
| Tree_seed0 | error | - | - | - | - | - | 60.030 | timeout |
  - `Tree_seed0`: Command '['/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--python', '/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/part_causal_graph_v0/part_causal_graph/blender_probe.py', '--', '--script', 'visual_validation/datasets/benchmark/categories/Tree_seed0/Tree_seed0.py', '--source-root', 'visual_validation/datasets/benchmark/categories/Tree_seed0', '--output', 'visual_validation/.model_playground_cache/.Tree_seed0-runtime-graph-5f0eaaf48cf97a48bbf2.raw.json', '--contact-ratio', '0.025', '--anchor-ratio', '0.025', '--max-nodes', '128', '--max-edges', '512', '--samples', '96']' timed out after 60 seconds
| TreeBaseCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.930 | single_final_mesh_no_runtime_relations |
| TreeFlower_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.076 | single_final_mesh_no_runtime_relations |
| TriangleShelf_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.557 | single_final_mesh_no_runtime_relations |
| TruncatedTree_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 6.585 | single_final_mesh_no_runtime_relations |
| TubeCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 10.148 | single_final_mesh_no_runtime_relations |
| TussockMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 13.895 | single_final_mesh_no_runtime_relations |
| TV_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.704 | single_final_mesh_no_runtime_relations |
| TVStand_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.554 | single_final_mesh_no_runtime_relations |
| TwigCoral_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.493 | single_final_mesh_no_runtime_relations |
| Urchin_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 9.803 | single_final_mesh_no_runtime_relations |
| UShapedStaircase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.698 | single_final_mesh_no_runtime_relations |
| Vase_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 8.855 | single_final_mesh_no_runtime_relations |
| VeratrumBranchMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.308 | single_final_mesh_no_runtime_relations |
| VeratrumEarMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 1.112 | single_final_mesh_no_runtime_relations |
| VeratrumMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 8.405 | single_final_mesh_no_runtime_relations |
| Volute_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 3.129 | single_final_mesh_no_runtime_relations |
| WallArt_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.552 | single_final_mesh_no_runtime_relations |
| WallShelf_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.619 | single_final_mesh_no_runtime_relations |
| WheatEarMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 2.198 | single_final_mesh_no_runtime_relations |
| WheatMonocot_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.302 | single_final_mesh_no_runtime_relations |
| Window_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 0.953 | single_final_mesh_no_runtime_relations |
| Wineglass_seed0 | ok | 1 | 0 | 0 | 0 | 0 | 4.100 | single_final_mesh_no_runtime_relations |
