# Textos largos de las paginas Mundo, Manual e Inicio.
from i18n import L

PILLARS = [
    ("explore", L("Explore", "Explorar"), L("Connected caverns, open surface and sealed ruins. Every route you find is knowledge you keep.",
                                             "Cavernas conectadas, superficie abierta y ruinas selladas. Cada ruta que encontrás es conocimiento que conservas.")),
    ("drill", L("Excavate", "Excavar"), L("Drilling is how you discover the world: it opens passages, pulls ore from the rock and reveals what was buried.",
                                           "Perforar es la forma de descubrir el mundo: abre pasajes, saca mineral de la roca y revela lo que estaba enterrado.")),
    ("gear", L("Equip", "Equiparse"), L("Thirteen gear slots, no class locks. Weapon, armor, battery and light are your build.",
                                         "Trece ranuras de equipo, sin bloqueos de clase. Arma, armadura, batería y luz son tu build.")),
    ("crew", L("Cooperate", "Cooperar"), L("Four civilisations, four roles. A crew that covers each other goes deeper and comes back.",
                                            "Cuatro civilizaciones, cuatro roles. Un equipo que se cubre llega más hondo y vuelve.")),
]

LOOP = [
    (L("Prepare", "Prepararse"), L("Pick your gear, charge your battery, pack ammunition.", "Elegí tu equipo, cargá la batería, llevá munición.")),
    (L("Descend", "Descender"), L("Ride the shaft lift or find a way down from the surface.", "Bajá en el elevador del pozo o encontrá un camino desde la superficie.")),
    (L("Fight & drill", "Pelear y perforar"), L("Clear threats, bore out ore, breach sealed walls.", "Despejá amenazas, extrae mineral, rompe muros sellados.")),
    (L("Decide", "Decidir"), L("Your light and your health are finite. Push deeper, or turn back?", "Tu luz y tu vida son finitas. ¿Bajar más o volver?")),
    (L("Return", "Volver"), L("Bring back what you secured and build your next expedition.", "Traé lo que aseguraste y armá tu próxima expedición.")),
]

REGIONS = [
    {
        "id": "outpost", "name": "The Outpost", "kind": L("Settlement", "Asentamiento"), "depth": "00",
        "img": "shots/world_outpost",
        "cap": L("The shaft lift in its pit, ringed with work lights; the newcomer crates wait on the pallet beside it.",
                 "El elevador del pozo en su foso, rodeado de luces de trabajo; los cajones para recién llegados esperan en el palé de al lado."),
        "lead": L("Where every operator arrives. A small fortified mining settlement built around an old excavation shaft.",
                  "Donde llega todo operador. Un pequeño asentamiento minero fortificado alrededor de un viejo pozo de excavación."),
        "body": L("From the arrival path you already see where you are going: the shaft, ringed with work lights, and the lift gantry right ahead. Workers drill the rock faces, cargo pods shuttle between the yard and the rim, and Old Brannock, the shaft miner, has three things to tell you: “New here?” · “Grab a drill. Grab a weapon.” · “Everything we need comes from below.”",
                  "Desde el camino de llegada ya ves adónde vas: el pozo, rodeado de luces de trabajo, y la grúa del elevador justo enfrente. Los trabajadores perforan la roca, las cápsulas de carga van y vienen entre el patio y el borde, y el viejo Brannock, minero del pozo, tiene tres cosas para decirte: «¿Nuevo por acá?» · «Agarrá un taladro. Agarrá un arma.» · «Todo lo que necesitamos viene de abajo.»"),
        "points": L(["Newcomer crates with your starter kit", "Shaft lift down to The Threshold (G)", "Adit stairs up to The Scarp",
                     "Two drill sites to try the drill", "Control station, power bay, cargo yard"],
                    ["Cajones para recién llegados con tu equipo inicial", "Elevador del pozo hacia The Threshold (G)",
                     "Escaleras del socavón hacia The Scarp", "Dos puntos de perforación para probar el taladro",
                     "Estación de control, sala de energía, patio de carga"]),
    },
    {
        "id": "threshold", "name": "The Threshold", "kind": L("Cavern", "Caverna"), "depth": "01",
        "img": "shots/world_threshold",
        "cap": L("The Threshold's three ways on: the metro portal to The Shallows, the deep shaft stairs to C-3 and the stairs up to The Scarp.",
                 "Las tres salidas de The Threshold: el portal del metro a The Shallows, las escaleras del pozo profundo a C-3 y las que suben a The Scarp."),
        "lead": L("The first cavern below the lift. Quiet, lit and safe enough to learn the basics.",
                  "La primera caverna bajo el elevador. Tranquila, iluminada y lo bastante segura para aprender lo básico."),
        "body": L("Painted signs teach you to move, equip gear from your loadout, switch on your lantern and dash. The lift takes you back up to the Outpost, the old metro tunnel leads on to The Shallows, and a deep shaft in the floor drops 140 m of stairs straight to Excavation C-3.",
                  "Carteles pintados te enseñan a moverte, equiparte desde el inventario, encender la linterna y usar el dash. El elevador te lleva de vuelta al Outpost, el viejo túnel del metro sigue hacia The Shallows y un pozo profundo en el piso baja 140 m de escaleras directo a Excavation C-3."),
        "points": L(["Move · WASD", "Loadout · I", "Lantern · T  ·  Dash · Q", "Metro · Line 2 to The Shallows",
                     "Deep shaft · stairs down to C-3", "Stairs up to The Scarp"],
                    ["Moverse · WASD", "Inventario · I", "Linterna · T  ·  Dash · Q", "Metro · Línea 2 a The Shallows",
                     "Pozo profundo · escaleras a C-3", "Escaleras que suben a The Scarp"]),
    },
    {
        "id": "shallows", "name": "The Shallows", "kind": L("Cavern · hunting ground", "Caverna · zona de caza"), "depth": "02",
        "img": "shots/world_shallows",
        "cap": L("The Keystone, the lumenita crystals and the Crawler nest in front of it.",
                 "The Keystone, los cristales de lumenita y el nido de Crawlers frente a ella."),
        "more": [("shots/world_shallows_ravager", L("The end of the Shallows: the Ravager lights its charge lane in front of the metro to C-3.",
                                                     "El final de The Shallows: el Ravager enciende el carril de su embestida frente al metro a C-3."))],
        "lead": L("A wide, damp cavern around a great stone column: The Keystone. The first real danger, and the first real ore.",
                  "Una caverna amplia y húmeda alrededor de una gran columna de piedra: The Keystone. El primer peligro real, y el primer mineral real."),
        "body": L("Limonite seams and hematite veins wait to be drilled; lumenita crystals glow cold blue near the Keystone. So does the Burrowborn: a Crawler nest sits in front of the Keystone, and at the far east end of the cave the Ravager waits in front of the metro down to C-3. Keep your distance and it charges; get close and it sweeps and slams. When it gets dark, follow the amber lamps back to The Threshold.",
                  "Vetas de limonita y hematita esperan el taladro; los cristales de lumenita brillan con azul frío cerca de The Keystone. También los Burrowborn: un nido de Crawlers frente a The Keystone y, al fondo este de la caverna, el Ravager esperando frente al metro que baja a C-3. Si mantenés distancia embiste; si te acercás barre y golpea. Cuando oscurezca, seguí las lámparas ámbar de vuelta a The Threshold."),
        "points": L(["Crawler nest · respawns every 25–45 s", "Ravager at the end of the cave · respawns every 90–150 s", "Limonite, hematite, lumenita",
                     "Ferrous samples on the ground · Scavengers"],
                    ["Nido de Crawlers · reaparecen cada 25–45 s", "El Ravager al final de la caverna · reaparece cada 90–150 s",
                     "Limonita, hematita, lumenita", "Muestras ferrosas en el suelo · Scavengers"]),
    },
    {
        "id": "c3", "name": "Excavation C-3", "kind": L("Excavation site", "Sitio de excavación"), "depth": "03",
        "img": "shots/world_c3",
        "cap": L("The C-3 dig: the metro from The Shallows, the lift cage up to The Threshold and the ore face.",
                 "La excavación C-3: el metro desde The Shallows, la jaula del elevador a The Threshold y el frente de mineral."),
        "lead": L("An active dig. “Authorised personnel.” The ore face is rich, and someone is paying people to keep it.",
                  "Una excavación activa. «Personal autorizado.» El frente de mineral es rico, y alguien le paga a gente para conservarlo."),
        "body": L("Hematite and hard magnetite lodes line the ore face, guarded by Excavation Enforcers. At the far end, a Deep Seal of basalt blocks the way. Drill through it and you find the Deep Survey Shaft, and the question of how far down the old surveys really went.",
                  "Filones de hematita y magnetita dura recorren el frente, custodiados por Excavation Enforcers. Al fondo, un Deep Seal de basalto bloquea el paso. Perforalo y vas a encontrar el Deep Survey Shaft, y la pregunta de hasta dónde llegaron realmente los viejos relevamientos."),
        "points": L(["Ore face · magnetite and hematite", "Excavation Enforcers ×2", "Lift up to The Threshold's deep shaft",
                     "Deep Seal · basalt, drill to breach", "Discovery: Deep Survey Shaft"],
                    ["Frente de mineral · magnetita y hematita", "Excavation Enforcers ×2", "Elevador al pozo profundo de The Threshold",
                     "Deep Seal · basalto, perforar para abrir", "Descubrimiento: Deep Survey Shaft"]),
    },
]

SURFACE = [
    {
        "id": "scarp", "name": "The Scarp", "kind": L("Surface", "Superficie"), "img": "shots/world_scarp",
        "cap": L("SHAFT 3: the headframe over the crater, the lift cage and the scavenger camp on the old road.",
                 "SHAFT 3: la torre sobre el cráter, la jaula del elevador y el campamento de carroñeros en la vieja ruta."),
        "lead": L("Open sky. A wide basin of cracked mud and hoodoo columns, cut by two canyons.",
                  "Cielo abierto. Una cuenca amplia de barro agrietado y columnas de roca, cortada por dos cañones."),
        "body": L("A scavenger camp works the old road. In the middle of the basin stands the SHAFT 3 headframe: its lift drops 120 m straight to The Threshold, and an old adit takes the stairs down to the Outpost. Both canyons lead on to The Saltpan.",
                  "Un campamento de carroñeros trabaja la vieja ruta. En el centro de la cuenca se levanta la torre del SHAFT 3: su elevador baja 120 m directo a The Threshold, y un viejo socavón baja por escaleras al Outpost. Los dos cañones siguen hacia The Saltpan."),
    },
    {
        "id": "saltpan", "name": "The Saltpan", "kind": L("Surface", "Superficie"), "img": "shots/world_saltpan",
        "cap": L("Surface dig C-7: the drill rig over the magnetite seam, under the sandstone cliffs.",
                 "La excavación de superficie C-7: el equipo de perforación sobre la veta de magnetita, bajo los acantilados de arenisca."),
        "lead": L("A salt flat under sandstone cliffs. “The convoy never reached the shaft.”",
                  "Un salar bajo acantilados de arenisca. «El convoy nunca llegó al pozo.»"),
        "body": L("A wrecked convoy lies along the old road, still holding scrap and a relic fragment. East is a ruined salt works; south, surface dig C-7, a magnetite seam waiting for a drill. Three scavengers think it is all theirs.",
                  "Un convoy destruido yace sobre la vieja ruta, todavía con chatarra y un fragmento de reliquia. Al este, unas salinas en ruinas; al sur, la excavación de superficie C-7, una veta de magnetita esperando un taladro. Tres carroñeros creen que todo es suyo."),
    },
]

EAST = [
    {
        "id": "frontier", "name": "Frontier Road", "kind": L("Surface · road", "Superficie · ruta"), "img": "shots/world_frontier_convoy",
        "cap": L("The convoy that never made it: a jack-knifed truck and its container across Frontier Road.",
                 "El convoy que nunca llegó: un camión cruzado y su contenedor sobre Frontier Road."),
        "more": [("shots/world_frontier_waystation", L("The waystation: a caravan stopped for the night, a fire and a keeper with news.",
                                                        "La parada: una caravana detenida para pasar la noche, un fuego y un encargado con noticias.")),
                 ("shots/world_frontier_cleft", L("The cleft off the road: stairs down to The Cinder Deep.", "La grieta junto a la ruta: escaleras que bajan a The Cinder Deep."))],
        "lead": L("East of The Saltpan the old road runs on through a long dry valley of relay pylons and wrecks.",
                  "Al este de The Saltpan la vieja ruta sigue por un valle seco y largo, con torres de relé y chatarra."),
        "body": L("A wrecked convoy still blocks half the road; past it, a waystation keeps water, shade and news for the caravans. In a cleft on the north side, stairs drop into The Cinder Deep. At the end of the valley, Dustline's gate.",
                  "Un convoy destruido todavía bloquea media ruta; más adelante, una parada guarda agua, sombra y noticias para las caravanas. En una grieta del lado norte, unas escaleras bajan a The Cinder Deep. Al final del valle, la puerta de Dustline."),
    },
    {
        "id": "dustline", "name": "Dustline", "kind": L("Trading city", "Ciudad del comercio"), "img": "shots/world_dustline_gate",
        "cap": L("The Frontier Gate under the neon DUSTLINE sign: everything has a price.", "La Frontier Gate bajo el neón de DUSTLINE: todo tiene un precio."),
        "more": [("shots/world_dustline_market", L("The Central Market: food and water, ammunition, medical, contracts and the trader.",
                                                    "El Mercado Central: comida y agua, munición, médico, contratos y el comerciante.")),
                 ("shots/world_dustline_exchange", L("The Exchange: bank, coin and the secure depot, above the market.",
                                                      "The Exchange: banco, moneda y el depósito seguro, sobre el mercado.")),
                 ("shots/world_dustline_yard", L("The Caravan Yard, where Rask shows weapons off the back of his truck.",
                                                 "El Patio de Caravanas, donde Rask muestra armas desde la caja de su camioneta."))],
        "lead": L("The trading city. Neutral ground where every civilisation buys, sells and hires.",
                  "La ciudad del comercio. Terreno neutral donde todas las civilizaciones compran, venden y contratan."),
        "body": L("Through the gate and the cargo inspection, the Gate Road runs up to the Central Market and the Exchange, where coin is banked and goods are kept. West is the Caravan Yard, east Scrapper's Row; the Lower Warrens are closed by order of the Exchange.",
                  "Pasando la puerta y la inspección de carga, la Gate Road sube hasta el Mercado Central y The Exchange, donde se guarda la moneda y la mercadería. Al oeste está el Patio de Caravanas, al este Scrapper's Row; los Lower Warrens están cerrados por orden del Exchange."),
    },
    {
        "id": "cinder", "name": "The Cinder Deep", "kind": L("Hunting ground · −90 m", "Coto de caza · −90 m"), "img": "shots/world_cinder_nest",
        "cap": L("The nest under the old aqueduct: the Greater Dragon beside the petrified egg.", "El nido bajo el viejo acueducto: el Gran Dragón junto al huevo petrificado."),
        "lead": L("Under the cleft off Frontier Road: galleries of an older people, swallowed by basalt. The Wyrms hunt here.",
                  "Bajo la grieta de Frontier Road: galerías de un pueblo antiguo tragadas por el basalto. Acá cazan los Wyrms."),
        "body": L("Four Dragons hunt the ash hall and the bridge gallery; a Greater Dragon keeps the nest. Come down the stairs, hunt, take the loot and climb back out: they return a minute or two later.",
                  "Cuatro Dragones cazan en el salón de ceniza y la galería del puente; un Gran Dragón cuida el nido. Bajá las escaleras, cazá, juntá el botín y volvé a subir: reaparecen un minuto o dos después."),
    },
]

CONCEPT_REGIONS = [
    ("tile_bastions", L("Bastions", "Bastiones"), L("Great underground cities. Trade, technology, life.", "Grandes ciudades subterráneas. Comercio, tecnología, vida.")),
    ("tile_frontier", L("The Frontier", "La Frontera"), L("Isolated settlements and expedition staging grounds.", "Asentamientos aislados y bases de expedición.")),
    ("tile_wilds", L("The Wilds", "Tierras Salvajes"), L("Caverns, underground rivers, fungal forests.", "Cavernas, ríos subterráneos, bosques de hongos.")),
    ("tile_works", L("Forgotten Works", "Obras Olvidadas"), L("Abandoned infrastructure of unknown origin.", "Infraestructura abandonada de origen desconocido.")),
    ("tile_deep", L("The Deep", "El Abismo"), L("The unknown is waiting.", "Lo desconocido te espera.")),
]

MACHINES = [
    ("machine_mule", "MULE", "class.foundry", L("Heavy · rugged", "Pesada · robusta")),
    ("machine_wraith", "WRAITH", "class.drift", L("Fast · precise", "Rápida · precisa")),
    ("machine_rootbreaker", "ROOTBREAKER", "class.verdant", L("Adaptive · biological", "Adaptativa · biológica")),
    ("machine_switchback", "SWITCHBACK", "class.relay", L("Modular · automated", "Modular · automatizada")),
]

CONTROLS = [
    ("W A S D", L("Move", "Moverse")),
    ("RMB", L("Hold to aim", "Mantener para apuntar")),
    ("LMB", L("Fire / strike while aiming", "Disparar / golpear apuntando")),
    ("Space", L("Quick attack on the nearest enemy", "Ataque rápido al enemigo más cercano")),
    ("Q", L("Mobility skill (Dash)", "Habilidad de movilidad (Dash)")),
    ("C", L("Class power", "Poder de clase")),
    ("T", L("Toggle lantern", "Encender / apagar linterna")),
    ("F", L("Hold to drill", "Mantener para perforar")),
    ("E", L("Pick up loot", "Recoger botín")),
    ("G", L("Use passage / lift / interact", "Usar pasaje / elevador / interactuar")),
    ("I", L("Loadout & inventory", "Equipo e inventario")),
    ("K", L("Skills", "Habilidades")),
    ("1–7", L("Quick slots", "Accesos rápidos")),
    ("Wheel", L("Zoom camera", "Zoom de cámara")),
]

FIRST_STEPS = [
    (L("Open your crates", "Abrí tus cajones"), L("Two newcomer crates wait in the Outpost. The Supply Crate has a backpack, the Leather Suit and a K6-3 helmet; the Gear Crate has your starting weapon (and rounds), a lantern, a battery and the Big Daddy drill. What's inside is yours alone.",
                                                  "Dos cajones para recién llegados te esperan en el Outpost. El Supply Crate trae una mochila, el Leather Suit y un casco K6-3; el Gear Crate trae tu arma inicial (y munición), una linterna, una batería y el taladro Big Daddy. Lo de adentro es sólo tuyo.")),
    (L("Equip everything", "Equipate todo"), L("Press I and drag each item onto its slot. Battery first: without it, your lantern and abilities have no energy.",
                                               "Presioná I y arrastrá cada objeto a su ranura. La batería primero: sin ella, tu linterna y tus habilidades no tienen energía.")),
    (L("Try the drill", "Probá el taladro"), L("Two drill sites sit by the shaft. Hold F at one and watch the rock give way.",
                                               "Hay dos puntos de perforación junto al pozo. Mantené F en uno y mirá cómo cede la roca.")),
    (L("Take the lift", "Tomá el elevador"), L("Press G at the shaft lift. The Threshold is quiet; The Shallows are not.",
                                              "Presioná G en el elevador del pozo. The Threshold es tranquila; The Shallows no.")),
    (L("Watch your battery", "Cuidá tu batería"), L("Your lantern drains energy and nothing recharges it out there. Light it when you need to see, turn it off when you don't.",
                                                   "La linterna consume energía y allá abajo nada la recarga. Prendela cuando necesites ver y apagala cuando no.")),
]
