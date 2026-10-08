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
        "img": "shots/phase13-outpost.jpg",
        "lead": L("Where every operator arrives. A small fortified mining settlement built around an old excavation shaft.",
                  "Donde llega todo operador. Un pequeño asentamiento minero fortificado alrededor de un viejo pozo de excavación."),
        "body": L("From the arrival path you already see where you are going: the shaft, ringed with work lights, and the lift gantry right ahead. Workers drill the rock faces, cargo pods shuttle between the yard and the rim, and Old Brannock, the shaft miner, has three things to tell you: “New here?” · “Grab a drill. Grab a weapon.” · “Everything we need comes from below.”",
                  "Desde el camino de llegada ya ves adónde vas: el pozo, rodeado de luces de trabajo, y la grúa del elevador justo enfrente. Los trabajadores perforan la roca, las cápsulas de carga van y vienen entre el patio y el borde, y el viejo Brannock, minero del pozo, tiene tres cosas para decirte: «¿Nuevo por acá?» · «Agarrá un taladro. Agarrá un arma.» · «Todo lo que necesitamos viene de abajo.»"),
        "points": L(["Newcomer crates with your starter kit", "Shaft lift down to The Threshold (G)", "Two drill sites to try the drill",
                     "Control station, power bay, cargo yard"],
                    ["Cajones para recién llegados con tu equipo inicial", "Elevador del pozo hacia The Threshold (G)",
                     "Dos puntos de perforación para probar el taladro", "Estación de control, sala de energía, patio de carga"]),
    },
    {
        "id": "threshold", "name": "The Threshold", "kind": L("Cavern", "Caverna"), "depth": "01",
        "img": "shots/region_threshold_gameplay.jpg",
        "lead": L("The first cavern below the lift. Quiet, lit and safe enough to learn the basics.",
                  "La primera caverna bajo el elevador. Tranquila, iluminada y lo bastante segura para aprender lo básico."),
        "body": L("Painted signs teach you to move, equip gear from your loadout, switch on your lantern and dash. Lifts on the walls take you back up to the Outpost, and the passages lead on to The Shallows.",
                  "Carteles pintados te enseñan a moverte, equiparte desde el inventario, encender la linterna y usar el dash. Los elevadores de las paredes te llevan de vuelta al Outpost, y los pasajes siguen hacia The Shallows."),
        "points": L(["Move · WASD", "Loadout · I", "Lantern · T  ·  Dash · Q", "Passage up from The Scarp"],
                    ["Moverse · WASD", "Inventario · I", "Linterna · T  ·  Dash · Q", "Pasaje que sube a The Scarp"]),
    },
    {
        "id": "shallows", "name": "The Shallows", "kind": L("Cavern · hunting ground", "Caverna · zona de caza"), "depth": "02",
        "img": "shots/region_b_shallows_keystone.jpg",
        "lead": L("A wide, damp cavern around a great stone column: The Keystone. The first real danger, and the first real ore.",
                  "Una caverna amplia y húmeda alrededor de una gran columna de piedra: The Keystone. El primer peligro real, y el primer mineral real."),
        "body": L("Limonite seams and hematite veins wait to be drilled; lumenita crystals glow cold blue near the Keystone. So does the Burrowborn: a Crawler nest guards the way down, and a Ravager holds the wide chamber beside it. When it gets dark, follow the amber lamps back to The Threshold.",
                  "Vetas de limonita y hematita esperan el taladro; los cristales de lumenita brillan con azul frío cerca de The Keystone. También los Burrowborn: un nido de Crawlers custodia la bajada y un Ravager domina la cámara de al lado. Cuando oscurezca, seguí las lámparas ámbar de vuelta a The Threshold."),
        "points": L(["Crawler nest · respawns every 25–45 s", "Ravager den · respawns every 90–150 s", "Limonite, hematite, lumenita",
                     "Ferrous samples on the ground · Scavengers"],
                    ["Nido de Crawlers · reaparecen cada 25–45 s", "Guarida del Ravager · reaparece cada 90–150 s",
                     "Limonita, hematita, lumenita", "Muestras ferrosas en el suelo · Scavengers"]),
    },
    {
        "id": "c3", "name": "Excavation C-3", "kind": L("Excavation site", "Sitio de excavación"), "depth": "03",
        "img": "shots/region_e_c3_dig.jpg",
        "lead": L("An active dig. “Authorised personnel.” The ore face is rich, and someone is paying people to keep it.",
                  "Una excavación activa. «Personal autorizado.» El frente de mineral es rico, y alguien le paga a gente para conservarlo."),
        "body": L("Hematite and hard magnetite lodes line the ore face, guarded by Excavation Enforcers. At the far end, a Deep Seal of basalt blocks the way. Drill through it and you find the Deep Survey Shaft, and the question of how far down the old surveys really went.",
                  "Filones de hematita y magnetita dura recorren el frente, custodiados por Excavation Enforcers. Al fondo, un Deep Seal de basalto bloquea el paso. Perforalo y vas a encontrar el Deep Survey Shaft, y la pregunta de hasta dónde llegaron realmente los viejos relevamientos."),
        "points": L(["Ore face · magnetite and hematite", "Excavation Enforcers ×2", "Deep Seal · basalt, drill to breach",
                     "Discovery: Deep Survey Shaft"],
                    ["Frente de mineral · magnetita y hematita", "Excavation Enforcers ×2", "Deep Seal · basalto, perforar para abrir",
                     "Descubrimiento: Deep Survey Shaft"]),
    },
]

SURFACE = [
    {
        "id": "scarp", "name": "The Scarp", "kind": L("Surface", "Superficie"), "img": "shots/surface_scarp.jpg",
        "lead": L("Open sky. A wide basin of cracked mud and hoodoo columns, cut by two canyons.",
                  "Cielo abierto. Una cuenca amplia de barro agrietado y columnas de roca, cortada por dos cañones."),
        "body": L("A scavenger camp works the old road. In the middle of the basin, an excavation crater and a Big Daddy rig: the shaft inside it drops straight to The Threshold. Both canyons lead on to The Saltpan.",
                  "Un campamento de carroñeros trabaja la vieja ruta. En el centro de la cuenca, un cráter de excavación y una torre Big Daddy: el pozo baja directo a The Threshold. Los dos cañones siguen hacia The Saltpan."),
    },
    {
        "id": "saltpan", "name": "The Saltpan", "kind": L("Surface", "Superficie"), "img": "shots/surface_saltpan.jpg",
        "lead": L("A salt flat under sandstone cliffs. “The convoy never reached the shaft.”",
                  "Un salar bajo acantilados de arenisca. «El convoy nunca llegó al pozo.»"),
        "body": L("A wrecked convoy lies along the old road, still holding scrap and a relic fragment. East is a ruined salt works; south, surface dig C-7, a magnetite seam waiting for a drill. Three scavengers think it is all theirs.",
                  "Un convoy destruido yace sobre la vieja ruta, todavía con chatarra y un fragmento de reliquia. Al este, unas salinas en ruinas; al sur, la excavación de superficie C-7, una veta de magnetita esperando un taladro. Tres carroñeros creen que todo es suyo."),
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
    (L("Open your crates", "Abrí tus cajones"), L("Two newcomer crates wait in the Outpost. The Supply Crate has a backpack, the Leather Suit and a K6-3 helmet; the Gear Crate has your doctrine's weapon (and rounds), a lantern, a battery and the Big Daddy drill. What's inside is yours alone.",
                                                  "Dos cajones para recién llegados te esperan en el Outpost. El Supply Crate trae una mochila, el Leather Suit y un casco K6-3; el Gear Crate trae el arma de tu doctrina (y munición), una linterna, una batería y el taladro Big Daddy. Lo de adentro es sólo tuyo.")),
    (L("Equip everything", "Equipate todo"), L("Press I and drag each item onto its slot. Battery first: without it, your lantern and abilities have no energy.",
                                               "Presioná I y arrastrá cada objeto a su ranura. La batería primero: sin ella, tu linterna y tus habilidades no tienen energía.")),
    (L("Try the drill", "Probá el taladro"), L("Two drill sites sit by the shaft. Hold F at one and watch the rock give way.",
                                               "Hay dos puntos de perforación junto al pozo. Mantené F en uno y mirá cómo cede la roca.")),
    (L("Take the lift", "Tomá el elevador"), L("Press G at the shaft lift. The Threshold is quiet; The Shallows are not.",
                                              "Presioná G en el elevador del pozo. The Threshold es tranquila; The Shallows no.")),
    (L("Watch your battery", "Cuidá tu batería"), L("Your lantern drains energy and nothing recharges it out there. Light it when you need to see, turn it off when you don't.",
                                                   "La linterna consume energía y allá abajo nada la recarga. Prendela cuando necesites ver y apagala cuando no.")),
]
