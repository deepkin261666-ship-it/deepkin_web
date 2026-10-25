# Capa de lore de la pagina Mundo (2026-10-11). Coherente con story.py (la historia) y los docs del juego
# (WORLD.md, DUSTLINE.md, DRAGON_LAIR.md, EXCAVATIONS.md, factions.json). Todo es PROVISIONAL como el juego:
# lo que no esta construido se cuenta como rumor. ES en rioplatense.
from i18n import L

TITLE = L("The world below, in brief", "El mundo de abajo, en breve")
LEAD = L("What every operator hears before the lift goes down. Read it next to the map: every place below is on it.",
         "Lo que todo operador escucha antes de que baje el elevador. Leelo al lado del mapa: cada lugar está en él.")

# (id, kicker, titulo, cuerpo, enlace opcional (href relativo a <lang>/), color opcional)
ENTRIES = [
    ("collapse", L("2148 · 2318", "2148 · 2318"), L("The Collapse", "El Colapso"),
     L("Around 2148 the connected world came apart: wars, failing infrastructure, machines that stopped behaving, and a theory nobody can prove — that a general intelligence had truly arrived. Archives vanished, satellites went quiet, and the old Internet broke into the Network: scattered nodes, forgotten servers, systems that still answer. A hundred and seventy years later nobody knows who, or what, is listening on 261.6.66.",
       "Cerca de 2148 el mundo conectado se vino abajo: guerras, infraestructura que fallaba, máquinas que dejaron de comportarse y una teoría que nadie puede probar: que una inteligencia general había llegado de verdad. Los archivos desaparecieron, los satélites se callaron y la vieja Internet se partió en la Red: nodos dispersos, servidores olvidados, sistemas que todavía contestan. Ciento setenta años después nadie sabe quién, o qué, escucha en 261.6.66."),
     "story.html#ch1", None),
    ("below", L("The age below", "La era de abajo"), L("Four civilisations", "Cuatro civilizaciones"),
     L("What was left of humanity went down. Shelters became cities, and cities became civilisations that agree on almost nothing — except that the surface belongs to the past. Each one sends its own kind of operator back up.",
       "Lo que quedó de la humanidad bajó. Los refugios se volvieron ciudades, y las ciudades, civilizaciones que no coinciden en casi nada, salvo en que la superficie pertenece al pasado. Cada una manda de vuelta arriba a su propio tipo de operador."),
     "story.html#ch2", None),
]

CIVS = [
    ("class.foundry", L("The Foundry", "La Forja"), "Ironhaven",
     L("Furnaces, rail yards and the heaviest machines in the world. Survival is something you build, maintain and endure.",
       "Hornos, playas ferroviarias y las máquinas más pesadas del mundo. Sobrevivir es algo que se construye, se mantiene y se aguanta.")),
    ("class.drift", L("The Drift", "La Deriva"), "Dustline",
     L("Frontier people, caravans and cartographers. Information, trade and exploration are the keys to prosperity.",
       "Gente de frontera, caravanas y cartógrafos. La información, el comercio y la exploración son las llaves de la prosperidad.")),
    ("class.verdant", L("The Verdant", "Lo Vivo"), "Verdant Reach",
     L("Gardens grown over old reservoirs. They learned to live with the strange underground ecosystems, weaving biology and technology.",
       "Jardines crecidos sobre viejos reservorios. Aprendieron a convivir con los extraños ecosistemas de abajo, tejiendo biología y tecnología.")),
    ("class.relay", L("The Relay", "La Red"), "Relay Nine",
     L("A city wired into an ancient relay station that still answers. They study what is left of the old Network.",
       "Una ciudad conectada a una antigua estación de relé que todavía contesta. Estudian lo que queda de la vieja Red.")),
]

MORE = [
    ("outpost", L("Where you start", "Donde empezás"), L("The Outpost and the shaft", "El Outpost y el pozo"),
     L("A small fortified mining settlement dug in 60 m down around an old excavation shaft. Newcomer crates, Old Brannock at his rock face, a terminal booth — and the lift car waiting in its well. The Shaft 3 elevator stops here on its way between the surface and The Threshold below.",
       "Un pequeño asentamiento minero fortificado, cavado a 60 m alrededor de un viejo pozo de excavación. Cajones para recién llegados, el viejo Brannock en su frente de roca, una cabina con terminal… y el elevador esperando en su pozo. El elevador del Pozo 3 para acá en su recorrido entre la superficie y The Threshold, abajo."),
     "wiki/zone-outpost.html"),
    ("dustline", L("Everything has a price", "Todo tiene un precio"), L("Dustline", "Dustline"),
     L("The largest trading settlement on the frontier, built from containers and recovered steel around a dead transport hub. Neutral ground where every civilisation buys, sells and hires — and where almost nothing is what it seems. Its unofficial rule: everything has a price; the only question is whether you can afford it.",
       "El mayor asentamiento comercial de la frontera, hecho de contenedores y acero recuperado alrededor de un viejo nodo de transporte. Terreno neutral donde todas las civilizaciones compran, venden y contratan, y donde casi nada es lo que parece. Su regla no escrita: todo tiene un precio; la única pregunta es si podés pagarlo."),
     "wiki/zone-dustline.html"),
    ("burrowborn", L("What hunts below", "Lo que caza abajo"), L("The Burrowborn", "Los Burrowborn"),
     L("Organic, mineral and wholly of the underground: dark wet hide, mineral plates, a faint green glow, eyes small or gone. They feel your footsteps through the stone long before they see you, and a hurt one calls its kind. Swarm, brute, alpha — and a Deepmaw nobody has met.",
       "Orgánicos, minerales y del todo subterráneos: piel oscura y húmeda, placas minerales, un leve brillo verde, ojos chicos o ausentes. Sienten tus pasos a través de la piedra mucho antes de verte, y uno herido llama a los suyos. Enjambre, bruto, alfa… y un Deepmaw que nadie conoció."),
     "wiki/faction-burrowborn.html"),
    ("castoffs", L("People, not monsters", "Gente, no monstruos"), L("The Castoffs", "The Castoffs"),
     L("Scavengers in long coats and balaclavas who live off the wreck yards, the old convoy roads and the first open shafts. Opportunists: they gang up on the lone operator and shout for each other, but they never go deep.",
       "Carroñeros de sobretodo y pasamontañas que viven de los desarmaderos, las viejas rutas de convoyes y los primeros pozos abiertos. Oportunistas: se juntan contra el operador solo y se llaman a los gritos, pero nunca bajan hondo."),
     "wiki/faction-castoffs.html"),
    ("wyrms", L("Under the cleft", "Bajo la grieta"), L("The Wyrms of the Cinder Deep", "Los Wyrms de The Cinder Deep"),
     L("Off Frontier Road a stair pit drops 90 m into galleries of an older people, swallowed by basalt. Solitary hunters that share one nest: they rear back before they breathe fire and lick their wounds when left alone. A Greater Dragon keeps the petrified egg. Hunt, take the loot, climb out — they come back.",
       "Junto a Frontier Road una escalera baja 90 m a galerías de un pueblo antiguo, tragadas por el basalto. Cazadores solitarios que comparten un nido: se echan hacia atrás antes de escupir fuego y se lamen las heridas si los dejás solos. Un Gran Dragón cuida el huevo petrificado. Cazá, juntá el botín, subí… vuelven."),
     "wiki/faction-wyrms.html"),
    ("excavations", L("Deeper still", "Más hondo todavía"), L("The excavations", "Las excavaciones"),
     L("The deeper you dig, the less certain history becomes. The Deep Survey, under the Shallows, is an old VDI survey: behind its Deep Seal the Dark Stratum (340 m) and the Relic Chamber (520 m), where relics older than the Collapse wait. One day an excavation contract bought in Dustline will call a giant drill to any wild map and carry a crew down floor by floor — as long as there is fuel.",
       "Cuanto más se cava, menos segura es la historia. The Deep Survey, bajo The Shallows, es un viejo relevamiento de VDI: detrás de su Sello Profundo, el Estrato Oscuro (340 m) y la Cámara de la Reliquia (520 m), donde esperan reliquias más viejas que el Colapso. Algún día un contrato de excavación comprado en Dustline va a llamar a un taladro gigante a cualquier mapa salvaje y bajar a una cuadrilla piso por piso… mientras haya combustible."),
     "wiki/zone-excavation-c3.html"),
]
