# Paginas de mecanicas de las Fases 2-7 del juego (2026-10-23, Fase 8 del sitio): grupo, drones, casas, excavaciones
# VDI, contratos, comercio y tiendas, comida, registros de lectura, municion por familias y armas de energia, baterias
# (recarga del Alquimista) y vehiculos (taller de motos, moto de carga y grua).
# Todo numero sale de data/ (copiado con build.py --sync) o de las constantes de las reglas del juego
# (data/rules/constants.json); los textos son EN + ES (voseo rioplatense). Fuente de verdad: los docs del juego
# (docs/PARTY.md, DRONES.md, INTERIORS.md, EXCAVATIONS.md, ECONOMY.md, ITEMS.md, COMBAT.md, VEHICLES.md, QUESTS.md).
# Se importa desde wiki.build() (wiki ya esta cargado), asi que puede usar sus helpers.
import glob
import json
import math
import os

import slugs as S
import wiki as K
from i18n import FAMILIES, L
from wiki import (CONST, FLOORS, ITEMS, MOBS, PEOPLE, QUESTS, REG, ROOT, VEHICLES, W, ZONES, article, e, has_icon, img, infobox,
                  item_cat, lk, n, pct, rel, sec, secs_toc, seealso, t, table, ul)

# --- Datos ---------------------------------------------------------------------------------------------------------
SHOPS = {}  # npc id -> shop (data/shops/*.json)
for _f in sorted(glob.glob(os.path.join(ROOT, "data", "shops", "*.json"))):
    SHOPS.update(json.load(open(_f)).get("shops", {}))
HOUSES = (K.jload("houses/houses.json") or {}).get("houses", {})
VEH = {v["id"]: v for v in VEHICLES}
CELL_ID = "item.battery.provisional_relay_cell"


def C(name, default):
    return CONST.get(name, default)


def shop_rows_for(item_id):
    """(npc id, buy, sell, stock) de cada tienda que vende o compra el objeto."""
    out = []
    for npc, sh in SHOPS.items():
        for g in sh.get("goods", []):
            if g["item"] == item_id:
                out.append((npc, g.get("buy"), g.get("sell"), g.get("stock")))
    return out


def price(v, lang):
    return (n(v, lang) + " Metal") if v is not None else "—"


def ilink(cid):
    return f'<span class="tn-in">{img(cid, "wk-ticon", 40)}{lk(cid)}</span>'


def mlink(slug, lang, anchor=""):
    return f'<a href="{slug}.html{("#" + anchor) if anchor else ""}">{e(t(MECH_NEW.get(slug, K.MECH.get(slug, slug)), lang))}</a>'


def steps(items):
    return '<ol class="wk-steps wk-plain">' + "".join(f"<li>{x}</li>" for x in items) + "</ol>"


def where(npc, lang):
    p = PEOPLE.get(npc)
    if not p or not p.get("zone"):
        return "—"
    sign, sub, _d = K.person_place(p)
    return lk(p["zone"]) + (f' · <span class="wk-sign">{e(sign)}</span>' if sign else "")


# --- Textos ----------------------------------------------------------------------------------------------------------
TX = {
    # titulos y descripciones de las tarjetas de mecanicas
    "m_party": L("Party", "Grupo"), "m_party_d": L("Follow, invites, the panel, shared XP", "Seguir, invitaciones, el panel, XP compartida"),
    "m_drones": L("Drones", "Drones"), "m_drones_d": L("Light, assault, scan and strike drones", "Drones de luz, asalto, escaneo y ataque"),
    "m_houses": L("Houses", "Casas"), "m_houses_d": L("Your Dustline container home, terminal and wall mounts", "Tu casa contenedor en Dustline, terminal y soportes de pared"),
    "m_excavations": L("Excavations (VDI)", "Excavaciones (VDI)"), "m_excavations_d": L("Call a drillship, the control room, generated floors", "Llamá un buque perforador, la sala de control, pisos generados"),
    "m_contracts": L("Contracts", "Contratos"), "m_contracts_d": L("Jobs from the board, paid on a crypto drive", "Trabajos del tablero, pagados en un drive cripto"),
    "m_trading": L("Trading & shops", "Comercio y tiendas"), "m_trading_d": L("Every trader, price and stock", "Cada comerciante, precio y stock"),
    "m_food": L("Food", "Comida"), "m_food_d": L("Heal over time, one meal at a time", "Curación en el tiempo, una comida por vez"),
    "m_logs": L("Reading Logs", "Registros de lectura"), "m_logs_d": L("Readable tablets and Document Cases", "Tablets legibles y Document Cases"),
    "m_ammo": L("Ammunition & energy weapons", "Munición y armas de energía"), "m_ammo_d": L("Ammo families, poison, heals, shots per cell", "Familias de munición, veneno, curas, disparos por celda"),
    "m_batteries": L("Batteries & recharge", "Baterías y recarga"), "m_batteries_d": L("Energy drains, spare cells, the Alchemist's recharge", "Consumos de energía, celdas de repuesto, la recarga del Alquimista"),
    # comunes
    "mx_how": L("How it works", "Cómo funciona"), "mx_rules": L("Rules", "Reglas"), "mx_play": L("Playing it", "Cómo se juega"),
    "mx_trader": L("Trader", "Comerciante"), "mx_buy": L("You pay", "Pagás"), "mx_sell": L("They pay", "Te pagan"), "mx_stock": L("Stock", "Stock"),
    "mx_price": L("Price", "Precio"), "mx_where": L("Where", "Dónde"), "mx_item": L("Item", "Objeto"), "mx_service": L("Service", "Servicio"),
    "mx_unlimited": L("unlimited", "sin límite"), "mx_per_run": L("{n} per server run", "{n} por sesión del servidor"),
    "mx_provisional": L("Prices and numbers are provisional balance and may change.", "Los precios y números son de balance provisorio y pueden cambiar."),
    "mx_trades": L("Trades", "Comercio"), "mx_traders_t": L("Bought and sold by", "Lo compran y venden"),
    "mx_none": L("Nothing", "Nada"),
    # comercio
    "tr_lead": L("Every trader in DEEPKIN uses the same counter: talk to them, pick BUY or SELL and the trade window opens. You pay with the coins you carry, never with the bank.",
                 "Todos los comerciantes de DEEPKIN usan el mismo mostrador: hablales, elegí BUY o SELL y se abre la ventana de comercio. Pagás con las monedas que llevás encima, nunca con el banco."),
    "tr_rules": L([
        "Talk to a trader (E) and choose BUY or SELL. BUY lists what they sell with price and stock; SELL lists what you carry that they buy. − / + set the quantity (Shift ×10).",
        "You must stand within 3.5 m of the trader, in the same zone. Walk away and the window closes.",
        "Purchases are paid in carried coins only: the pouch and your worn backpack. Coins in a spare bag or in the bank do not count; withdraw at a 261.6.66 terminal first.",
        "Change comes back in the largest coins. A trade that would not fit your cells or carry limit is refused and nothing moves.",
        "You can only sell what sits in your top-level cargo cells; a bag must be empty to be sold.",
        "A trader never buys something back for more than they sell it. Limited stock is per server run and resets when the server restarts.",
        "The server keeps its own copy of every price: the window only shows them.",
    ], [
        "Hablale a un comerciante (E) y elegí BUY o SELL. BUY lista lo que vende con precio y stock; SELL lista lo que llevás que él compra. − / + cambian la cantidad (Shift ×10).",
        "Tenés que estar a menos de 3,5 m del comerciante, en la misma zona. Si te alejás, la ventana se cierra.",
        "Las compras se pagan sólo con monedas encima: la bolsa y tu mochila puesta. Las monedas de una bolsa de repuesto o del banco no cuentan; sacalas antes en una terminal 261.6.66.",
        "El vuelto vuelve en las monedas más grandes. Si la compra no entra en tus celdas o en tu límite de carga, se rechaza y no se mueve nada.",
        "Sólo podés vender lo que está en las celdas de primer nivel de tu inventario; una bolsa tiene que estar vacía para venderla.",
        "Un comerciante nunca te recompra algo más caro de lo que lo vende. El stock limitado es por sesión del servidor y se repone cuando el servidor reinicia.",
        "El servidor tiene su propia copia de cada precio: la ventana sólo los muestra.",
    ]),
    "tr_traders": L("The traders", "Los comerciantes"), "tr_services": L("Services", "Servicios"),
    "tr_services_lead": L("Some counters sell services instead of goods.", "Algunos mostradores venden servicios en vez de mercadería."),
    "tr_recharge": L("Recharges one empty battery cell: {price} Metal + {q} × {reagent}", "Recarga una celda de batería vacía: {price} Metal + {q} × {reagent}"),
    "tr_vehicle": L("Sells the {v} for {price} Metal", "Vende la {v} a {price} Metal"),
    "tr_crane": L("Crane service: hauls one of your stranded bikes to the shop for {p} of its price", "Servicio de grúa: trae al taller una de tus motos varadas por el {p} de su precio"),
    "tr_property": L("Sells {what} for {price} Metal", "Vende {what} a {price} Metal"),
    "tr_no_goods": L("Sells services only.", "Sólo vende servicios."),
    # comida
    "food_lead": L("Food heals slowly: the health of a meal is released evenly over its eating time instead of at once.",
                   "La comida cura despacio: la vida de una comida se libera de a poco durante el tiempo que tardás en comerla, en vez de toda junta."),
    "food_rules": L([
        "Eat from the cargo or a hotkey, like a capsule. One unit is spent and its health arrives a little every tick until the meal ends.",
        "One meal at a time: a second one is refused with the time left (\"Still eating\").",
        "At full health the server refuses the meal and nothing is spent.",
        "A meal has its own timer: you can still crack a Health Capsule while you eat, and food ignores the capsule cooldown.",
        "Death ends the meal. Meals are not saved: a disconnect loses what was left of it.",
    ], [
        "Comé desde el inventario o una tecla rápida, como una cápsula. Se gasta una unidad y la vida llega de a poco en cada tick hasta que termina la comida.",
        "Una comida por vez: una segunda se rechaza con el tiempo que falta (\"Still eating\").",
        "Con la vida llena el servidor rechaza la comida y no se gasta nada.",
        "La comida tiene su propio contador: podés usar una Health Capsule mientras comés, y la comida no respeta el enfriamiento de la cápsula.",
        "Morir corta la comida. Las comidas no se guardan: si te desconectás, perdés lo que faltaba.",
    ]),
    "food_t": L("Food and healing", "Comida y curación"), "food_heal": L("Heals", "Cura"), "food_time": L("Over", "Durante"),
    "food_rate": L("Per second", "Por segundo"), "food_cost_hp": L("Metal per 10 HP", "Metal cada 10 PV"),
    "food_instant": L("at once", "de golpe"),
    # registros
    "logs_lead": L("Reading Logs are tablets with text on them: field notes, ledgers, memos and telemetry left behind by VDI and the Castoffs.",
                   "Los registros de lectura son tablets con texto: notas de campo, libros de cuentas, memos y telemetría que dejaron VDI y los Castoffs."),
    "logs_rules": L([
        "Right-click a log in your cargo or a bag → READ, or double-click it. The tablet opens in the middle of the screen and types its text; ES / EN switches language when the log has both.",
        "Reading spends nothing, and the log stays an ordinary item (one per cell, 0.3 kg): drop it, store it in the depot or carry it.",
        "Movement is blocked while the reader is open; Esc or CLOSE closes it. The world keeps running.",
        "A quest can ask you to read a log (goal \"read item\").",
    ], [
        "Clic derecho sobre un registro en tu inventario o en una bolsa → READ, o doble clic. La tablet se abre en el medio de la pantalla y escribe su texto; ES / EN cambia el idioma cuando el registro tiene los dos.",
        "Leer no gasta nada y el registro sigue siendo un objeto común (uno por celda, 0,3 kg): podés tirarlo, guardarlo en el depósito o llevarlo.",
        "No te podés mover mientras el lector está abierto; Esc o CLOSE lo cierran. El mundo sigue andando.",
        "Una misión puede pedirte que leas un registro (objetivo \"read item\").",
    ]),
    "logs_cases": L("Where logs are found", "Dónde se encuentran"),
    "logs_cases_lead": L("Most logs sit in Document Cases: fixed containers that glow faint cyan. Every operator finds their own copy, and a case is empty for you once you carry its log. Boss crates hold the rest; they open once per operator.",
                         "La mayoría está en Document Cases: contenedores fijos con un brillo cian tenue. Cada operador encuentra su propia copia, y un estuche está vacío para vos si ya llevás su registro. El resto está en los cofres de los jefes, que se abren una vez por operador."),
    "logs_list": L("The logs", "Los registros"), "logs_title": L("Title on the tablet", "Título en la tablet"),
    "logs_found": L("Found in", "Se encuentra en"), "logs_lang": L("Languages", "Idiomas"),
    # municion
    "ammo_lead": L("Every ranged weapon fires only its own ammunition family; energy weapons fire from your battery cell instead.",
                   "Cada arma a distancia dispara sólo su propia familia de munición; las armas de energía disparan de tu celda de batería."),
    "ammo_rules": L([
        "The weapon loads the first stack of its family in your top-level cargo; other families are skipped (a Spore Projector never fires Field Rounds).",
        "The stronger kind of a family (Hardened, Virulent, Surge) is drawn heavier for everyone.",
        "The HUD ammo panel names the family and the loaded kind (ROUNDS · FIELD, SPORES · VIRULENT, SYNAPSE · SURGE); for an energy weapon it reads CELL · cost per shot.",
        "Ammunition multipliers scale the weapon hit; poison ticks and heals are flat (no class or skill scaling).",
    ], [
        "El arma carga la primera pila de su familia en las celdas de primer nivel de tu inventario; las otras familias se saltean (un Spore Projector nunca dispara Field Rounds).",
        "La variante fuerte de cada familia (Hardened, Virulent, Surge) se dibuja más pesada para todos.",
        "El panel de munición del HUD nombra la familia y lo que está cargado (ROUNDS · FIELD, SPORES · VIRULENT, SYNAPSE · SURGE); con un arma de energía dice CELL · costo por disparo.",
        "Los multiplicadores de munición escalan el golpe del arma; los ticks de veneno y las curas son fijos (no escalan con clase ni habilidad).",
    ]),
    "ammo_fams": L("The families", "Las familias"), "ammo_family": L("Family", "Familia"), "ammo_weapons": L("Weapons", "Armas"),
    "ammo_effect": L("Effect", "Efecto"), "ammo_mult": L("Damage", "Daño"),
    "fam_rounds": L("Rounds", "Balas"), "fam_spores": L("Spores", "Esporas"), "fam_synapse": L("Synapse", "Sinapsis"), "fam_energy": L("Energy", "Energía"),
    "eff_poison": L("poisons {p}/s for {s} s ({tot} total)", "envenena {p}/s durante {s} s ({tot} en total)"),
    "eff_heal": L("heals an ally {h}", "cura {h} a un aliado"),
    "eff_area": L("; on an enemy hit heals every operator within {r} m of you (you too) for {h}", "; al pegarle a un enemigo cura {h} a cada operador a {r} m tuyo (a vos también)"),
    "eff_dmg": L("damage only", "sólo daño"),
    "spores_t": L("Spores: poison", "Esporas: veneno"),
    "spores_p": L("A hit poisons the creature: flat ticks once a second, credited to the shooter (kill XP and aggro). Hitting it again keeps the tick clock and takes the stronger poison and the later end: poison does not stack. It only affects creatures.",
                  "Un golpe envenena a la criatura: ticks fijos una vez por segundo, acreditados a quien disparó (XP de la muerte y agresión). Volver a pegarle mantiene el ritmo y se queda con el veneno más fuerte y el final más tardío: el veneno no se acumula. Sólo afecta a criaturas."),
    "synapse_t": L("Synapse: healing darts", "Sinapsis: dardos que curan"),
    "synapse_p": L("Aimed at (or clicked on) another operator, a dart heals instead of damaging: there is no friendly fire. The nearest operator on the line of fire wins over an enemy farther along it. Heals cap at full health and never revive; a heal trains Vitalism. A dart at a full-health ally is still spent.",
                   "Apuntado (o con clic) sobre otro operador, un dardo cura en vez de dañar: no hay fuego amigo. El operador más cercano en la línea de tiro gana sobre un enemigo más lejos. Las curas no pasan de la vida máxima y nunca reviven; curar entrena Vitalismo. Un dardo a un aliado con la vida llena se gasta igual."),
    "energy_t": L("Energy weapons", "Armas de energía"),
    "energy_p": L("Tech ranged weapons load no rounds: every shot draws {c} energy from your worn battery cell. Below one shot's cost the trigger is refused (NO CHARGE). A bare {cap}-energy cell holds {s} shots; hits train Tech. The energy readout counts sustained fire as a drain.",
                  "Las armas a distancia de Tecnología no cargan balas: cada disparo saca {c} de energía de tu celda puesta. Si no alcanza para un disparo, el gatillo se rechaza (NO CHARGE). Una celda sola de {cap} de energía tiene {s} disparos; los golpes entrenan Tecnología. El indicador de energía cuenta el fuego sostenido como un consumo."),
    "shots_cell": L("Shots per cell", "Disparos por celda"), "per_shot": L("Energy per shot", "Energía por disparo"),
    "exec_t": L("Short Blades: executions", "Hojas cortas: ejecuciones"),
    "exec_p": L("Any Short Blades hit (Twin Blades, Relay Knife) on a humanoid creature at or below {p} of its health finishes it: the hit deals at least its remaining health and plays an execution. The server decides it; dragons, Burrowborn and other non-humanoids are never executed.",
                "Cualquier golpe de Hojas cortas (Twin Blades, Relay Knife) a una criatura humanoide con {p} de vida o menos la remata: el golpe hace por lo menos la vida que le queda y se ve una ejecución. Lo decide el servidor; los dragones, los Burrowborn y otros no humanoides nunca se ejecutan."),
    # baterias
    "bat_lead": L("Your battery cell is your energy: lights, drones, energy weapons and class powers all draw from the cell you wear.",
                  "Tu celda de batería es tu energía: las luces, los drones, las armas de energía y los poderes de clase sacan de la celda que llevás puesta."),
    "bat_drains": L("What drains it", "Qué la consume"), "bat_source": L("Source", "Fuente"), "bat_cost": L("Cost", "Costo"),
    "bat_lasts": L("A full cell lasts", "Una celda llena dura"),
    "per_s": L("{v} per second", "{v} por segundo"), "per_shot_v": L("{v} per shot", "{v} por disparo"), "per_use": L("{v} per use", "{v} por uso"),
    "bat_power": L("Class power", "Poder de clase"), "bat_dash": L("Dash", "Dash"),
    "bat_spares_t": L("Spare cells", "Celdas de repuesto"),
    "bat_spares": L("Carry spare cells in your pouch or worn backpack (never inside a spare bag) and the server moves charge from the fullest spare into the worn cell at {r} energy a second, with no loss. Regen pauses in combat (5 s after the last hit given or taken): the spares are a reserve between fights, not a heal. Spares keep their charge across logins. The Outpost Gear Crate gives three cells.",
                     "Llevá celdas de repuesto en la bolsa o en la mochila puesta (nunca dentro de una bolsa de repuesto) y el servidor pasa carga de la más llena a la celda puesta a {r} de energía por segundo, sin pérdida. La regeneración se pausa en combate (5 s después del último golpe dado o recibido): los repuestos son una reserva entre peleas, no una cura. Los repuestos conservan la carga entre sesiones. El Gear Crate del Outpost trae tres celdas."),
    "bat_recharge_t": L("Recharge at the Alchemist", "Recarga en el Alquimista"),
    "bat_recharge": L("{who} refills one empty cell (charge at or below {empty}) for {price} carried Metal + {q} × {reagent}; the same cell comes back full. It shows as a blue service row under BUY that names what is missing.",
                      "{who} recarga una celda vacía (carga de {empty} o menos) por {price} Metal encima + {q} × {reagent}; la misma celda vuelve llena. Aparece como una fila azul de servicio bajo BUY que te dice qué te falta."),
    "bat_buy": L("A new cell costs {price} Metal at {who}: more than eight recharges, so recharging is the cheap way to keep a cell and a new one is for when you have no Lumenita or want another spare.",
                 "Una celda nueva cuesta {price} Metal en {who}: más que ocho recargas, así que recargar es la forma barata de mantener una celda y una nueva es para cuando no tenés Lumenita o querés otro repuesto."),
    "bat_vdi": L("Empty cells are also what you pour into a VDI drillship's energy reserve (load energy).", "Las celdas también se vuelcan en la reserva de energía de un buque perforador VDI (load energy)."),
    "lumenita_src": L("Where Lumenita comes from", "De dónde sale la Lumenita"),
    # grupo
    "party_lead": L("Operators group up from the field: right-click another operator to follow them or invite them to a party.",
                    "Los operadores se agrupan en el campo: clic derecho sobre otro operador para seguirlo o invitarlo al grupo."),
    "party_play": L([
        "A quick right-click on another operator in your zone opens a menu: FOLLOW and INVITE TO PARTY (greyed with the reason when you cannot invite).",
        "Follow walks you toward them and stops {stop} m short; any movement key ends it. The server checks that movement like any other, so following gives no advantage.",
        "An invite shows a toast with ACCEPT / DECLINE and a bar that drains over {s} s. A newer invite replaces an older one.",
        "The party panel (left, under your plate) lists every member: level, callsign, the zone they stand in, health and battery percentage. The leader toggles SHARED XP and can PROMOTE or KICK; anyone can LEAVE.",
    ], [
        "Un clic derecho corto sobre otro operador de tu zona abre un menú: FOLLOW e INVITE TO PARTY (en gris con el motivo cuando no podés invitar).",
        "Seguir te lleva hacia él y frena a {stop} m; cualquier tecla de movimiento lo corta. El servidor valida ese movimiento como cualquier otro, así que seguir no da ventaja.",
        "Una invitación muestra un aviso con ACCEPT / DECLINE y una barra que se vacía en {s} s. Una invitación nueva reemplaza a la anterior.",
        "El panel del grupo (a la izquierda, bajo tu placa) muestra a cada miembro: nivel, indicativo, la zona donde está, vida y porcentaje de batería. El líder prende SHARED XP y puede PROMOTE o KICK; cualquiera puede LEAVE.",
    ]),
    "party_rules": L([
        "Up to {max} members. Invite only an online operator in your zone within {r} m who is not in a party; if you are in a party you must lead it.",
        "The party is created on the first accept, with the inviter as leader. A leaving leader passes the lead to the longest-standing member; a party left with one member disbands.",
        "Kick, promote and the shared-XP switch are for the leader only. Shared XP survives a change of leader.",
        "Parties live only while the server runs: a disconnect is a leave and nothing is saved.",
        "Members see each other's zone, level, health and battery percentage wherever they stand, never positions, cargo or exact energy.",
        "A scan drone's radar is shared with the whole party, wherever each member stands.",
    ], [
        "Hasta {max} miembros. Sólo podés invitar a un operador conectado de tu zona, a menos de {r} m, que no esté en un grupo; si estás en un grupo, tenés que ser el líder.",
        "El grupo se crea con la primera aceptación, con quien invitó como líder. Un líder que se va le pasa el mando al miembro más antiguo; un grupo que queda con uno solo se disuelve.",
        "Expulsar, promover y el interruptor de XP compartida son sólo del líder. La XP compartida sigue prendida si cambia el líder.",
        "Los grupos existen mientras el servidor corre: desconectarse es irse, y no se guarda nada.",
        "Los miembros ven la zona, el nivel, la vida y el porcentaje de batería de los demás estén donde estén, nunca la posición, el inventario ni la energía exacta.",
        "El radar de un dron de escaneo se comparte con todo el grupo, esté donde esté cada miembro.",
    ]),
    "party_xp_t": L("Shared experience", "Experiencia compartida"),
    "party_xp": L("With SHARED XP on, the kill XP the members earned is pooled and split equally among the members in the kill's zone within {r} m of the creature, whether or not they hit it, as long as the lowest level among them is at least 2/3 of the highest. Otherwise (or with fewer than two in range) each keeps their own damage share. Players outside the party are untouched.",
                  "Con SHARED XP prendido, la XP de la muerte que ganaron los miembros se junta y se reparte en partes iguales entre los miembros que estén en la zona a menos de {r} m de la criatura, le hayan pegado o no, siempre que el nivel más bajo entre ellos sea al menos 2/3 del más alto. Si no (o si hay menos de dos en rango), cada uno se queda con su parte por daño. A los jugadores de afuera del grupo no les cambia nada."),
    "party_ex": L("Example", "Ejemplo"), "party_ex_lead": L("A {xp} XP kill, three members in range, levels {a}, {b} and {c}:", "Una muerte de {xp} XP, tres miembros en rango, niveles {a}, {b} y {c}:"),
    "party_ex_ok": L("{lo} ≥ 2/3 × {hi} = {lim}: each gets {each} XP.", "{lo} ≥ 2/3 × {hi} = {lim}: cada uno recibe {each} XP."),
    "party_ex_no": L("With levels {a} and {b}: {a} < 2/3 × {b} = {lim}, so the panel shows LV GAP and each keeps their own share.",
                     "Con niveles {a} y {b}: {a} < 2/3 × {b} = {lim}, así que el panel muestra LV GAP y cada uno se queda con su parte."),
    "callsign_note": L("Operators have no chosen names yet: the party shows a callsign like RELAY·001 (class and number).", "Los operadores todavía no eligen nombre: el grupo muestra un indicativo como RELAY·001 (clase y número)."),
    # drones
    "dr_lead": L("Drones are cargo items you launch to fly for a while: a lamp, a gun, a scout or a bomb.", "Los drones son objetos del inventario que lanzás para que vuelen un rato: una lámpara, un arma, un explorador o una bomba."),
    "dr_rules": L([
        "Launch from a cargo cell (double-click, or right-click → DEPLOY DRONE) or from a hotkey; the same key recalls it. The key reads AIR while it flies.",
        "The item never leaves your cargo: it is marked DEPLOYED and comes back when you recall it, the cell runs dry, its flight time ends, the item leaves your cargo, you die or you disconnect. A following drone can never be lost.",
        "While it flies it draws energy from your worn cell (spare-cell regen still applies). Launching needs at least {s} s of flight in the cell.",
        "One drone per operator: launching another recalls the first.",
        "Only its owner commands it; there is no command that names someone else's drone.",
    ], [
        "Se lanza desde una celda del inventario (doble clic, o clic derecho → DEPLOY DRONE) o desde una tecla rápida; la misma tecla lo llama de vuelta. La tecla dice AIR mientras vuela.",
        "El objeto nunca sale de tu inventario: queda marcado DEPLOYED y vuelve cuando lo llamás, cuando la celda se vacía, cuando termina su tiempo de vuelo, cuando el objeto sale de tu inventario, cuando morís o cuando te desconectás. Un dron que te sigue nunca se pierde.",
        "Mientras vuela saca energía de tu celda puesta (la regeneración de los repuestos sigue funcionando). Para lanzarlo hacen falta por lo menos {s} s de vuelo en la celda.",
        "Un dron por operador: lanzar otro llama de vuelta al primero.",
        "Sólo su dueño lo controla; no hay comando que nombre el dron de otro.",
    ]),
    "dr_table": L("The drones", "Los drones"), "dr_fn": L("Function", "Función"), "dr_drain": L("Drain", "Consumo"), "dr_flight": L("Flight", "Vuelo"),
    "dr_stats": L("Key numbers", "Números clave"), "dr_tech": L("Tech", "Tecnología"),
    "fn_light": L("Light", "Luz"), "fn_assault": L("Assault", "Asalto"), "fn_scan": L("Scan (piloted)", "Escaneo (pilotado)"), "fn_kamikaze": L("Strike (piloted, spent)", "Ataque (pilotado, se gasta)"),
    "st_lamp": L("lamp {r} m", "lámpara {r} m"), "st_gun": L("{d} dmg (max {m}) every {i} s, {rg} m", "{d} de daño (máx. {m}) cada {i} s, {rg} m"),
    "st_scan": L("{sp} m/s, {cr} m range, radar {sr} m", "{sp} m/s, {cr} m de alcance, radar {sr} m"),
    "st_blast": L("{sp} m/s, {cr} m range, blast {br} m, {d} (max {m})", "{sp} m/s, {cr} m de alcance, explosión {br} m, {d} (máx. {m})"),
    "dr_follow_t": L("Following drones: light and assault", "Drones que te siguen: luz y asalto"),
    "dr_follow": L([
        "They hover at a fixed offset beside you, keep up at 7.5 m/s, jump to you if left 14 m behind and cross passages with you.",
        "The assault drone fights your fight: the creature you last hit or, if you are not fighting anything else, the one that last hit you (for {m} s). It never picks its own targets and holds fire while you ride.",
        "Each shot spends one Field or Hardened round from your cargo (at most 24 a flight); with none it does not launch. Its damage scales with the round and your Tech, capped at {cap}, then ×{el} against elites and ×{bo} against bosses. You get the aggro, the damage share, the kill XP and the quest kills.",
    ], [
        "Flotan a tu lado a una distancia fija, te siguen a 7,5 m/s, saltan hasta vos si quedan 14 m atrás y cruzan los pasajes con vos.",
        "El dron de asalto pelea tu pelea: la criatura a la que le pegaste último o, si no estás peleando con otra, la que te pegó último (durante {m} s). Nunca elige blancos propios y no dispara mientras manejás.",
        "Cada disparo gasta una Field o Hardened round de tu inventario (máximo 24 por vuelo); sin balas no despega. Su daño escala con la bala y tu Tecnología, con tope {cap}, y después ×{el} contra élites y ×{bo} contra jefes. La agresión, la parte del daño, la XP y las muertes de misión son tuyas.",
    ]),
    "dr_pilot_t": L("Piloted drones: scan and strike", "Drones pilotados: escaneo y ataque"),
    "dr_pilot": L([
        "You stand still and fly them with the movement keys, holding a laptop (scan) or a rugged tablet (strike). Moving, getting hit, mounting a vehicle or changing zone drops the link and the drone ends its flight.",
        "Scan drones: the camera follows the ground under the drone. Every half second its radar marks creatures (by tier), ore, loot and operators within its radius, for you and your party. When the scan ends the overlay clears.",
        "Strike drones fly in first person (A / D turn, W throttle, S brake). They arm after half a second and blow up on a wall, the ground, a creature within reach, DETONATE (Space or its key), or when the flight time, the cell or the link runs out.",
        "The blast hits up to 8 creatures in its radius (not behind a wall), from full damage at the centre to {edge} at the edge, capped at {cap}, then ×{el} elites, ×{bo} bosses. Players are never hurt. One drone is spent per blast.",
    ], [
        "Te quedás quieto y los volás con las teclas de movimiento, con una laptop (escaneo) o una tablet reforzada (ataque) en las manos. Moverte, recibir un golpe, subirte a un vehículo o cambiar de zona corta el enlace y el dron termina su vuelo.",
        "Drones de escaneo: la cámara sigue el suelo bajo el dron. Cada medio segundo su radar marca criaturas (por nivel), mineral, botín y operadores dentro de su radio, para vos y tu grupo. Cuando termina el escaneo, la capa se borra.",
        "Los drones de ataque vuelan en primera persona (A / D giran, W acelera, S frena). Se arman a los medio segundo y explotan contra una pared, el suelo, una criatura al alcance, con DETONATE (Espacio o su tecla) o cuando se acaba el tiempo de vuelo, la celda o el enlace.",
        "La explosión golpea hasta 8 criaturas en su radio (no detrás de una pared), del daño completo en el centro al {edge} en el borde, con tope {cap}, y después ×{el} élites, ×{bo} jefes. Nunca lastima a jugadores. Cada explosión gasta un dron.",
    ]),
    "dr_where": L("Rask sells them in Dustline for now; their home is Relay Nine.", "Por ahora los vende Rask en Dustline; su origen es Relay Nine."),
    # casas
    "ho_lead": L("A private container apartment in Dustline, bought from the house agent and walked in first person.", "Un departamento contenedor privado en Dustline, que le comprás a la agente inmobiliaria y recorrés en primera persona."),
    "ho_play": L([
        "Buy it from {agent} by the CONTAINER HOMES board, east of the Lower Warrens shacks near the East Gate road. Her dialog leads with BUY; the trade window lists the house and its upgrade. Paid in carried coins.",
        "The steel door (UNIT 7) only opens for its owner (\"LOCKED · OWNER ONLY\"); on foot only. Inside, the view switches to first person: WASD to move, the mouse to look, E to use, G for the door.",
        "Every owner stands in a private copy of the room: two owners at home at the same time never see each other.",
        "No combat inside: attacks, powers and drone launches are refused.",
    ], [
        "Comprala a {agent}, junto al cartel CONTAINER HOMES, al este de las casillas de los Lower Warrens, cerca del camino de la East Gate. Su diálogo empieza con BUY; la ventana de comercio lista la casa y su mejora. Se paga con monedas encima.",
        "La puerta de acero (UNIT 7) sólo se abre para su dueño (\"LOCKED · OWNER ONLY\"); sólo a pie. Adentro la vista pasa a primera persona: WASD para moverte, el mouse para mirar, E para usar, G para la puerta.",
        "Cada dueño está en una copia privada del cuarto: dos dueños en casa al mismo tiempo nunca se ven.",
        "Adentro no hay combate: se rechazan ataques, poderes y lanzamientos de drones.",
    ]),
    "ho_terminal_t": L("The terminal upgrade", "La mejora de terminal"),
    "ho_terminal": L("The {name} upgrade installs a 261.6.66 computer on the desk under the window: the same BANK and DEPOT apps as the Exchange, from home. Before the upgrade the desk holds a crate marked NOT INSTALLED.",
                     "La mejora {name} instala una computadora 261.6.66 en el escritorio bajo la ventana: las mismas apps BANK y DEPOT del Exchange, desde tu casa. Antes de la mejora, en el escritorio hay un cajón que dice NOT INSTALLED."),
    "ho_mounts_t": L("Wall mounts", "Soportes de pared"),
    "ho_mounts": L("The room has {n} wall slots. E on an empty slot opens a picker with your cargo cells: the whole cell (a stack, a charged battery, a bag with its contents) goes on the wall and shows its own model. TAKE puts it back. Mounted items are not in your cargo, so death never reaches them.",
                   "El cuarto tiene {n} soportes de pared. E sobre uno vacío abre un selector con las celdas de tu inventario: la celda entera (una pila, una batería cargada, una bolsa con lo que tiene) va a la pared y se ve su modelo. TAKE la devuelve. Lo colgado no está en tu inventario, así que la muerte nunca lo alcanza."),
    "ho_slot": L("Slot", "Soporte"), "ho_prices": L("Prices", "Precios"),
    # excavaciones
    "ex_lead": L("Vantage Deep Industries will drop a drillship anywhere open you call it and bore floors for you: generated per call-out, not fixed zones.",
                 "Vantage Deep Industries te tira un buque perforador en cualquier lugar abierto donde lo llames y perfora pisos para vos: se generan en cada llamado, no son zonas fijas."),
    "ex_play": L([
        "Get an Expedition Service: {agent} sells it for {price} Metal, and his contract {quest} gives the first one free.",
        "Use it (double-click, its right-click menu or a hotkey): the ship lands {ahead} m ahead of you. Not in settlements, underground, on roads, near passages, arrivals or fuel stations, at a map's edge, within {sp} m of another ship, or on ground that is not open and clear. The service is spent; you are the Owner; one open excavation per owner.",
        "For {drop} s an amber ring marks the site while the ship falls; anyone under it is pushed to the edge. Then it stays: a huge cylinder with one door and a floor display.",
        "Roster members press E at the door: inside is the first-person control room (no combat). E at the terminal opens the VDI Excavation software; E at the door steps out on the floor the ship is on.",
        "The owner closes it (close, then close confirm): everyone is put back on the surface, the floors and everything in them are removed and the ground is free again.",
    ], [
        "Conseguí un Expedition Service: {agent} lo vende a {price} Metal, y su contrato {quest} te da el primero gratis.",
        "Usalo (doble clic, su menú del clic derecho o una tecla rápida): el buque aterriza {ahead} m adelante tuyo. No en asentamientos, bajo tierra, en caminos, cerca de pasajes, llegadas o estaciones de combustible, en el borde del mapa, a menos de {sp} m de otro buque, ni en suelo que no esté abierto y libre. El servicio se gasta; sos el Owner; una excavación abierta por dueño.",
        "Durante {drop} s un anillo ámbar marca el lugar mientras el buque cae; a quien esté debajo lo empuja al borde. Después se queda: un cilindro enorme con una puerta y un cartel de piso.",
        "Los miembros de la lista apretan E en la puerta: adentro está la sala de control en primera persona (sin combate). E en la terminal abre el software VDI Excavation; E en la puerta te deja en el piso donde está el buque.",
        "El dueño la cierra (close, después close confirm): todos vuelven a la superficie, los pisos y todo lo que hay en ellos desaparece y el suelo queda libre otra vez.",
    ]),
    "ex_soft_t": L("The VDI Excavation software", "El software VDI Excavation"),
    "ex_cmd": L("Command", "Comando"), "ex_does": L("What it does", "Qué hace"),
    "ex_cmds": [("status", L("the ship, its floor, reserves and roster", "el buque, su piso, reservas y lista")),
                ("roster", L("who is on the roster and where they stand", "quién está en la lista y dónde está")),
                ("reserves", L("energy and fuel in the ship", "energía y combustible del buque")),
                ("invite <callsign> · remove <callsign>", L("owner: add or remove a member (up to {max})", "dueño: suma o saca un miembro (hasta {max})")),
                ("load energy", L("pours your fullest spare battery cell into the reserve (the cell stays, empty)", "vuelca tu celda de repuesto más llena en la reserva (la celda queda, vacía)")),
                ("load fuel", L("pours your fullest gas can into the reserve (the can stays, empty)", "vuelca tu bidón más lleno en la reserva (el bidón queda, vacío)")),
                ("floor <n> · descend · ascend", L("moves the ship (0 = surface)", "mueve el buque (0 = superficie)")),
                ("close · close confirm", L("owner: ends the excavation", "dueño: termina la excavación")),
                ("connect 261.6.66", L("times out: VDI ships are off the DEEPKIN network", "no responde: los buques VDI están fuera de la red de DEEPKIN"))],
    "ex_res_t": L("Reserves and floors", "Reservas y pisos"),
    "ex_res": L("The ship arrives with {e0} energy and {f0} L of fuel (max {emax} / {fmax}). Each leg down to depth d costs {ed}·d energy and {fd}·d L, so the costs add up as you go deeper; going up is free. A trip locks the door for {tr} s. The ship will not leave a floor while a member still stands on it. The number of floors is rolled per excavation from the map's danger: 2–3 in the starting areas, up to {mx}.",
                "El buque llega con {e0} de energía y {f0} L de combustible (máx. {emax} / {fmax}). Cada tramo hacia abajo hasta la profundidad d cuesta {ed}·d de energía y {fd}·d L, así que los costos se suman a medida que bajás; subir es gratis. Un viaje traba la puerta {tr} s. El buque no deja un piso mientras haya un miembro parado en él. La cantidad de pisos se sortea en cada excavación según el peligro del mapa: 2–3 en las zonas iniciales, hasta {mx}."),
    "ex_cost": L("Cost to go down from the surface", "Costo para bajar desde la superficie"), "ex_depth": L("Depth", "Profundidad"),
    "ex_persist": L("Open excavations survive a server restart (the ship stands again on the surface, reserves and roster kept); floors are regenerated from their seed with fresh creatures and resources. Creatures, drops and remains below are lost on a restart or a close.",
                    "Las excavaciones abiertas sobreviven a un reinicio del servidor (el buque vuelve a estar en la superficie, con reservas y lista); los pisos se regeneran desde su semilla con criaturas y recursos nuevos. Las criaturas, el botín y los restos de abajo se pierden con un reinicio o al cerrar."),
    "ex_fixed": L("Not to be confused with Excavation C-3 under the Scarp: that is an old, fixed VDI dig you reach by the Shaft 3 elevator.",
                  "No confundir con Excavation C-3 bajo el Scarp: ésa es una excavación vieja y fija de VDI a la que se llega por el elevador del Shaft 3."),
    # contratos
    "co_lead": L("A contract is a job with a crypto payment: the employer pays on a Contract Drive that you cash at any bank terminal.",
                 "Un contrato es un trabajo con pago cripto: el empleador paga con un Contract Drive que cobrás en cualquier terminal del banco."),
    "co_rules": L([
        "Take the paper from the giver, do the job, then come back: the last step hands you the drive.",
        "Cash it at the BANK app of any 261.6.66 terminal: type insert drive (or click the hint). One drive is taken from your cargo and its value is credited to your balance.",
        "A drive in a spare bag does not count, and a drive that would push your balance past its limit stays with you.",
        "Until then it is an ordinary item: it can be dropped, picked up by anyone, stored in the depot or lost when you die. A drive pays whoever slots it.",
    ], [
        "Agarrá el papel del que da el trabajo, hacé el trabajo y volvé: el último paso te entrega el drive.",
        "Cobralo en la app BANK de cualquier terminal 261.6.66: escribí insert drive (o hacé clic en la pista). Se saca un drive de tu inventario y su valor se acredita en tu saldo.",
        "Un drive dentro de una bolsa de repuesto no cuenta, y un drive que pasaría tu saldo por encima del límite se queda con vos.",
        "Hasta entonces es un objeto común: se puede tirar, cualquiera lo puede levantar, guardar en el depósito o perder al morir. Un drive le paga a quien lo enchufa.",
    ]),
    "co_list": L("Contracts", "Contratos"), "co_giver": L("Giver", "Lo da"), "co_pays": L("Pays", "Paga"), "co_job": L("Job", "Trabajo"),
    "co_drives": L("Drives", "Drives"), "co_value": L("Value", "Valor"),
    "vdi_quest": L("Also from a board-style job: the VDI agent's {q} hands over a free Expedition Service instead of a drive.",
                   "También como trabajo: {q} del agente de VDI te da un Expedition Service gratis en vez de un drive."),
    # vehiculos
    "ve_cmp": L("The machines", "Las máquinas"), "ve_hold": L("Hold", "Baúl"), "ve_hold_v": L("{c} cells · {kg} kg", "{c} celdas · {kg} kg"),
    "ve_price": L("Price at the bike shop", "Precio en el taller"), "ve_crane": L("Crane haul", "Grúa"),
    "ve_shop_t": L("The bike shop", "El taller de motos"),
    "ve_shop": L("MOTO · DUSTLINE is a small garage against the Caravan Yard's north fence. {who} sells the bikes and runs the crane; sold and craned bikes park on the painted bay in front ({spots} spots).",
                 "MOTO · DUSTLINE es un garaje chico contra el alambrado norte del Caravan Yard. {who} vende las motos y maneja la grúa; las motos vendidas y rescatadas se estacionan en la bahía pintada de enfrente ({spots} lugares)."),
    "ve_shop_rules": L([
        "Buying: stand within reach of the dealer, pay in carried coins (not the bank), own fewer than {max} vehicles and leave a free spot in the bay. The new bike arrives with its starting fuel, a full frame and an empty hold.",
        "Crane: hauls one of your stranded bikes of that kind (empty tank or wrecked frame, not ridden) from anywhere to the bay for {p} of its list price. It does not refuel: buy a can at the gate station.",
        "No sale back to the shop; the crane picks the first stranded bike of the kind.",
    ], [
        "Comprar: parate cerca del vendedor, pagá con monedas encima (no con el banco), tené menos de {max} vehículos y dejá un lugar libre en la bahía. La moto nueva llega con su combustible inicial, el chasis entero y el baúl vacío.",
        "Grúa: trae a la bahía, desde donde esté, una de tus motos varadas de ese tipo (tanque vacío o chasis destruido, sin nadie arriba) por el {p} de su precio de lista. No carga combustible: comprá un bidón en la estación de la puerta.",
        "El taller no recompra; la grúa elige la primera moto varada de ese tipo.",
    ]),
    "ve_hold_t": L("The cargo motorcycle's hold", "El baúl de la moto de carga"),
    "ve_hold_p": L("The {name} carries a hold of {c} cells and up to {kg} kg. Click the bike (or press I beside it) to open it like a ground bag: only its owner, within 4 m or riding it, flat items only (no bags). The hold is saved with the bike.",
                   "La {name} lleva un baúl de {c} celdas y hasta {kg} kg. Hacé clic en la moto (o apretá I al lado) para abrirlo como una bolsa en el suelo: sólo su dueño, a menos de 4 m o arriba de ella, sólo objetos sueltos (sin bolsas). El baúl se guarda con la moto."),
    # faccion: planeados
    "planned_members": L("Planned", "Planeados"),
}
W.update(TX)

MECH_NEW = {"party": "m_party", "drones": "m_drones", "houses": "m_houses", "excavations": "m_excavations", "contracts": "m_contracts",
            "trading": "m_trading", "food": "m_food", "reading-logs": "m_logs", "ammunition": "m_ammo", "batteries": "m_batteries"}
K.MECH.update(MECH_NEW)


def lst(key, lang, **kw):
    return [x.format(**kw) if kw else x for x in TX[key][lang]]


def mech(lang, slug, lead_key, body, box=""):
    return K.mech_article(lang, slug, t(lead_key, lang), body, box)


def drop_sources(item_id, lang):
    rows = sorted(K.DROPPED.get(item_id, []), key=lambda x: -x[1])
    return ", ".join(f"{lk(m)} ({pct(ch, lang)})" for m, ch, _a, _b in rows)


# --- Comercio --------------------------------------------------------------------------------------------------------
def shop_services(npc, sh, lang):
    out = []
    rc = sh.get("recharge")
    if rc:
        out.append(f'{t("tr_recharge", lang, price=n(rc["price"], lang), q=n(rc.get("reagent_quantity", 1), lang), reagent=lk(rc["reagent"]))} · {mlink("batteries", lang, "recharge")}')
    for v in sh.get("vehicles", []):
        name = VEH.get(v["vehicle"], {}).get("display_name", v["vehicle"])
        out.append(f'{e(t("tr_vehicle", lang, v=name, price=n(v["buy"], lang)))} · {mlink("vehicles", lang, "bike-shop")}')
    if sh.get("crane"):
        out.append(f'{e(t("tr_crane", lang, p=pct(sh["crane"]["fraction"], lang)))}')
    for pr in sh.get("property", []):
        name = HOUSES.get(pr["id"], {}).get("name") or next((u["name"] for h in HOUSES.values() for k, u in h.get("upgrades", {}).items() if k == pr["id"]), pr["id"])
        out.append(f'{e(t("tr_property", lang, what=name, price=n(pr["buy"], lang)))} · {mlink("houses", lang)}')
    return out


def goods_table(sh, lang):
    rows = [[ilink(g["item"]), price(g.get("buy"), lang), price(g.get("sell"), lang),
             n(g["stock"], lang) if g.get("stock") else (e(t("mx_unlimited", lang)) if g.get("buy") is not None else "—")] for g in sh.get("goods", [])]
    if not rows:
        return ""
    return table([(t("mx_item", lang), "text"), (t("mx_buy", lang), "num"), (t("mx_sell", lang), "num"), (t("mx_stock", lang), "num")], rows, sortable=False)


def page_trading(lang):
    body = sec("how", t("mx_how", lang), steps([e(x) for x in lst("tr_rules", lang)]) + f'<p class="note">{e(t("mx_provisional", lang))}</p>')
    blocks = ""
    for npc, sh in sorted(SHOPS.items(), key=lambda kv: (PEOPLE.get(kv[0], {}).get("zone") or "", PEOPLE.get(kv[0], {}).get("name", kv[0]))):
        p = PEOPLE.get(npc, {})
        role = f' <small>{e(p.get("role", ""))}</small>' if p.get("role") else ""
        svc = shop_services(npc, sh, lang)
        inner = goods_table(sh, lang) + (ul(svc) if svc else "")
        if not sh.get("goods") and not svc:
            inner = f'<p>{e(t("tr_no_goods", lang))}</p>'
        blocks += f'<article class="wk-skill" id="{e(npc.split(".")[-1].replace("_", "-"))}"><h3>{lk(npc)}{role}</h3><p class="wk-sub">{where(npc, lang)}</p>{inner}</article>'
    body += sec("traders", t("tr_traders", lang), blocks)
    svc = []
    for npc, sh in SHOPS.items():
        for x in shop_services(npc, sh, lang):
            svc.append(f"{lk(npc)}: {x}")
    vdi = [f'{lk(npc)}: {ilink(g["item"])} · {mlink("excavations", lang)}' for npc, sh in SHOPS.items() for g in sh.get("goods", []) if item_cat(g["item"]) == "service"]
    body += sec("services", t("tr_services", lang), f'<p>{e(t("tr_services_lead", lang))}</p>' + ul(svc + vdi))
    body += seealso(lang, [f'<a href="currency.html">{e(t("m_currency", lang))}</a>', mlink("batteries", lang), mlink("food", lang), mlink("vehicles", lang),
                           mlink("houses", lang), mlink("excavations", lang), lk("zone.dustline")])
    return mech(lang, "trading", "tr_lead", body)


def item_trade_section(it, lang):
    """Seccion "Lo compran y venden" de la ficha de un objeto."""
    rows = [[lk(npc), where(npc, lang), price(b, lang), price(s, lang), n(st, lang) if st else ("—" if b is None else e(t("mx_unlimited", lang)))]
            for npc, b, s, st in shop_rows_for(it["id"])]
    if not rows:
        return ""
    return sec("traders", t("mx_traders_t", lang), table([(t("mx_trader", lang), "text"), (t("mx_where", lang), "text"), (t("mx_buy", lang), "num"),
                                                          (t("mx_sell", lang), "num"), (t("mx_stock", lang), "num")], rows, sortable=False)
               + f'<p class="wk-sub">{mlink("trading", lang)}</p>')


def person_trade_section(p, lang):
    sh = SHOPS.get(p["id"])
    if not sh:
        return ""
    svc = shop_services(p["id"], sh, lang)
    return sec("trades", t("mx_trades", lang), goods_table(sh, lang) + (ul(svc) if svc else "") + f'<p class="wk-sub">{mlink("trading", lang)}</p>')


def item_mech_links(it, lang):
    """Enlaces a mecanicas para "Ver tambien" de un objeto."""
    cat = item_cat(it["id"])
    out = {"drone": ["drones", "batteries"], "food": ["food"], "log": ["reading-logs"], "contract": ["contracts"], "service": ["excavations"],
           "ammunition": ["ammunition"], "battery": ["batteries"], "light": ["batteries"]}.get(cat, [])
    if it.get("weapon_type") == "ranged" or it.get("weapon_family") == "skill.blades":
        out.append("ammunition")
    if it["id"] == "item.container.document_case":
        out.append("reading-logs")
    if shop_rows_for(it["id"]):
        out.append("trading")
    return [mlink(s, lang) for s in dict.fromkeys(out)]


# --- Comida ----------------------------------------------------------------------------------------------------------
def page_food(lang):
    rows = []
    for it in sorted(ITEMS.values(), key=lambda i: i["display_name"]):
        p = it.get("properties", {})
        if item_cat(it["id"]) not in ("food", "consumable") or not p.get("heal_amount"):
            continue
        secs_ = p.get("heal_seconds", 0)
        buy = min((b for _n, b, _s, _st in shop_rows_for(it["id"]) if b is not None), default=None)
        rows.append([ilink(it["id"]), "+" + n(p["heal_amount"], lang), (n(secs_, lang) + " s") if secs_ else e(t("food_instant", lang)),
                     n(p["heal_amount"] / secs_, lang, 1) if secs_ else "—", price(buy, lang), n(buy / p["heal_amount"] * 10, lang, 1) if buy else "—",
                     n(p.get("stack_size", 1), lang), n(it.get("weight", 0), lang) + " kg"])
    body = sec("table", t("food_t", lang), table([(t("mx_item", lang), "text"), (t("food_heal", lang), "num"), (t("food_time", lang), "text"),
                                                   (t("food_rate", lang), "num"), (t("mx_price", lang), "num"), (t("food_cost_hp", lang), "num"),
                                                   (t("stack", lang), "num"), (t("weight", lang), "num")], rows))
    body += sec("rules", t("mx_rules", lang), ul([e(x) for x in lst("food_rules", lang)]))
    food = [it["id"] for it in ITEMS.values() if item_cat(it["id"]) == "food"]
    sellers = sorted({npc for f in food for npc, b, _s, _st in shop_rows_for(f) if b is not None})
    body += seealso(lang, [lk(x) for x in food] + [lk(s) for s in sellers] + [lk("item.consumable.health_capsule"), mlink("trading", lang)])
    return mech(lang, "food", "food_lead", body)


# --- Registros de lectura ----------------------------------------------------------------------------------------
def page_logs(lang):
    body = sec("how", t("mx_how", lang), ul([e(x) for x in lst("logs_rules", lang)]))
    rows = []
    for it in sorted(ITEMS.values(), key=lambda i: i["display_name"]):
        if item_cat(it["id"]) != "log":
            continue
        lg = it.get("log", {})
        found = []
        for kind, a, _q, _x in K.FOUND.get(it["id"], []):
            if kind == "crate":
                zones = [x[1] for x in K.FOUND.get(a, []) if x[0] == "placed"]
                found.append(lk(a) + (" · " + ", ".join(dict.fromkeys(lk(z) for z in zones)) if zones else ""))
            elif kind in ("placed", "ground"):
                found.append(lk(a))
        # Estuches colocados que nombran su registro en el propio registro de la entidad.
        for en in K.REGION.get("entities", []):
            if it["id"] in (en.get("crate_loot") or []):
                found.append(lk(en["content_id"]) + " · " + lk(en["zone_id"]))
        langs = "EN" + (" · ES" if lg.get("text_es") else "")
        rows.append([ilink(it["id"]), f'<span class="wk-sign">{e(lg.get("title", ""))}</span>', "<br>".join(dict.fromkeys(found)) or "—", langs])
    body += sec("cases", t("logs_cases", lang), f'<p>{e(t("logs_cases_lead", lang))}</p>'
                + table([(t("mx_item", lang), "text"), (t("logs_title", lang), "text"), (t("logs_found", lang), "text"), (t("logs_lang", lang), "text")], rows, sortable=False, cls="wrap-cells"))
    body += seealso(lang, [lk("item.container.document_case"), f'<a href="quests.html">{e(t("quests", lang))}</a>'])
    return mech(lang, "reading-logs", "logs_lead", body)


# --- Municion y armas de energia ------------------------------------------------------------------------------------
def weapon_family(w):
    a = ITEMS.get(w.get("ammo_item_id") or "", {})
    if w.get("properties", {}).get("energy_per_shot"):
        return "energy"
    return a.get("ammo_family", "rounds") if a else None


def ammo_effect(a, lang):
    p = a.get("properties", {})
    out = []
    if p.get("poison_per_second"):
        out.append(t("eff_poison", lang, p=n(p["poison_per_second"], lang), s=n(p["poison_seconds"], lang), tot=n(p["poison_per_second"] * p["poison_seconds"], lang)))
    if p.get("ally_heal") or p.get("heal_ally") or p.get("heal_amount"):
        out.append(t("eff_heal", lang, h=n(p.get("ally_heal") or p.get("heal_ally") or p.get("heal_amount"), lang)))
    if p.get("surge_heal"):
        out[-1:] = [(out[-1] if out else "") + t("eff_area", lang, r=n(p.get("surge_radius", 6), lang), h=n(p["surge_heal"], lang))]
    return "; ".join(out) or t("eff_dmg", lang)


def page_ammo(lang):
    body = sec("how", t("mx_how", lang), ul([e(x) for x in lst("ammo_rules", lang)]))
    ranged = [w for w in ITEMS.values() if w.get("weapon_type") == "ranged" and not w.get("planned")]
    rows = []
    for fam in ("rounds", "spores", "synapse"):
        ammo = [a for a in ITEMS.values() if item_cat(a["id"]) == "ammunition" and a.get("ammo_family", "rounds") == fam]
        ws = [w for w in ranged if weapon_family(w) == fam]
        for i, a in enumerate(ammo):
            rows.append([e(t("fam_" + fam, lang)) if i == 0 else "", ", ".join(lk(w["id"]) for w in ws) if i == 0 else "", ilink(a["id"]),
                         "×" + n(a.get("properties", {}).get("ammo_multiplier", 1), lang), e(ammo_effect(a, lang))])
    ew = [w for w in ranged if weapon_family(w) == "energy"]
    cap = ITEMS.get(CELL_ID, {}).get("properties", {}).get("battery_capacity", 100)
    if ew:
        cost = ew[0]["properties"]["energy_per_shot"]
        rows.append([e(t("fam_energy", lang)), ", ".join(lk(w["id"]) for w in ew), lk(CELL_ID), "—", e(t("per_shot_v", lang, v=n(cost, lang)))])
    body += sec("families", t("ammo_fams", lang), table([(t("ammo_family", lang), "text"), (t("ammo_weapons", lang), "text"), (t("ammo", lang), "text"),
                                                         (t("ammo_mult", lang), "num"), (t("ammo_effect", lang), "text")], rows, sortable=False, cls="wrap-cells"))
    body += sec("spores", t("spores_t", lang), f'<p>{e(t("spores_p", lang))}</p>')
    body += sec("synapse", t("synapse_t", lang), f'<p>{e(t("synapse_p", lang))}</p>')
    if ew:
        cost = ew[0]["properties"]["energy_per_shot"]
        erows = [[ilink(w["id"]), n(w["properties"]["energy_per_shot"], lang), n(math.floor(cap / w["properties"]["energy_per_shot"]), lang),
                  n(K.base_damage(w), lang), n(w["properties"].get("attack_interval", 1), lang) + " s"] for w in ew]
        body += sec("energy", t("energy_t", lang), f'<p>{e(t("energy_p", lang, c=n(cost, lang), cap=n(cap, lang), s=n(math.floor(cap / cost), lang)))}</p>'
                    + table([(t("ammo_weapons", lang), "text"), (t("per_shot", lang), "num"), (t("shots_cell", lang), "num"), (t("damage", lang), "num"),
                             (t("interval", lang), "num")], erows, sortable=False) + f'<p class="wk-sub">{mlink("batteries", lang)}</p>')
    blades = [w for w in ITEMS.values() if w.get("weapon_family") == "skill.blades" and not w.get("planned")]
    body += sec("executions", t("exec_t", lang), f'<p>{e(t("exec_p", lang, p=pct(C("EXECUTE_HEALTH_RATIO", 0.25), lang)))}</p>'
                + '<p class="wk-see">' + " · ".join(lk(w["id"]) for w in blades) + "</p>")
    sellers = sorted({npc for a in ITEMS.values() if item_cat(a["id"]) == "ammunition" for npc, b, _s, _st in shop_rows_for(a["id"]) if b is not None})
    body += seealso(lang, [lk(s) for s in sellers] + [mlink("trading", lang), f'<a href="skills.html">{e(t("m_skills", lang))}</a>', '<a href="../arsenal.html">Arsenal</a>'])
    return mech(lang, "ammunition", "ammo_lead", body)


def execution_section(it, lang):
    if it.get("weapon_family") != "skill.blades":
        return ""
    return sec("executions", t("exec_t", lang), f'<p>{e(t("exec_p", lang, p=pct(C("EXECUTE_HEALTH_RATIO", 0.25), lang)))}</p>')


# --- Baterias ------------------------------------------------------------------------------------------------------
def page_batteries(lang):
    cell = ITEMS.get(CELL_ID, {})
    cap = cell.get("properties", {}).get("battery_capacity", 100)
    rows = []
    for it in sorted(ITEMS.values(), key=lambda i: i["display_name"]):
        p = it.get("properties", {})
        if it.get("planned"):
            continue
        if p.get("light_energy_per_second"):
            v = p["light_energy_per_second"]
            rows.append([ilink(it["id"]), e(t("per_s", lang, v=n(v, lang))), "≈ " + n(cap / v / 60, lang, 1) + " min"])
        elif it.get("drone"):
            v = it["drone"]["energy_per_second"]
            rows.append([ilink(it["id"]), e(t("per_s", lang, v=n(v, lang))), "≈ " + n(cap / v / 60, lang, 1) + " min"])
        elif p.get("energy_per_shot"):
            v = p["energy_per_shot"]
            rows.append([ilink(it["id"]), e(t("per_shot_v", lang, v=n(v, lang))), n(math.floor(cap / v), lang) + " " + t("shots_cell", lang).lower()])
    rows.append([e(t("bat_power", lang)), e(t("per_use", lang, v=n(K.G.COMBAT.get("ABILITY_ENERGY_COST", 15), lang))), n(math.floor(cap / K.G.COMBAT.get("ABILITY_ENERGY_COST", 15)), lang) + "×"])
    rows.append([e(t("bat_dash", lang)), e(t("per_use", lang, v=n(K.G.COMBAT.get("DASH_ENERGY_COST", 6), lang))), n(math.floor(cap / K.G.COMBAT.get("DASH_ENERGY_COST", 6)), lang) + "×"])
    body = sec("drains", t("bat_drains", lang), table([(t("bat_source", lang), "text"), (t("bat_cost", lang), "text"), (t("bat_lasts", lang), "text")], rows, sortable=False))
    body += sec("spares", t("bat_spares_t", lang), f'<p>{e(t("bat_spares", lang, r=n(C("RATE", 1.0), lang)))}</p>')
    rc_npc, rc = next(((k, v["recharge"]) for k, v in SHOPS.items() if v.get("recharge")), (None, None))
    if rc:
        txt = t("bat_recharge", lang, who=lk(rc_npc), empty=pct(rc.get("empty_below", 0.05), lang), price=n(rc["price"], lang),
                q=n(rc.get("reagent_quantity", 1), lang), reagent=lk(rc["reagent"]))
        new = next(((npc, b) for npc, b, _s, _st in shop_rows_for(CELL_ID) if b is not None), None)
        extra = f'<p>{t("bat_buy", lang, price=n(new[1], lang), who=lk(new[0]))}</p>' if new else ""
        src = drop_sources(rc["reagent"], lang)
        body += sec("recharge", t("bat_recharge_t", lang), f'<p>{txt}</p>{extra}'
                    + (f'<p><b>{e(t("lumenita_src", lang))}:</b> {src}</p>' if src else "") + f'<p class="note">{e(t("mx_provisional", lang))}</p>')
    body += sec("vdi", t("m_excavations", lang), f'<p>{e(t("bat_vdi", lang))} {mlink("excavations", lang, "reserves")}</p>')
    box = infobox(cell.get("display_name", "Battery Cell I"), img(CELL_ID), [(t("capacity", lang), n(cap, lang) + " " + t("energy", lang).lower()),
                                                                           (t("weight", lang), n(cell.get("weight", 1), lang) + " kg"), ("ID", f"<code>{CELL_ID}</code>")])
    body += seealso(lang, [lk(CELL_ID), mlink("ammunition", lang, "energy"), mlink("drones", lang), mlink("trading", lang)])
    return mech(lang, "batteries", "bat_lead", body, box)


# --- Grupo ---------------------------------------------------------------------------------------------------------
def page_party(lang):
    mx, rr, sr, inv = C("MAX_MEMBERS", 4), C("INVITE_RANGE", 40), C("SHARE_RANGE", 30), C("INVITE_SECONDS", 60)
    body = sec("play", t("mx_play", lang), ul([e(x) for x in lst("party_play", lang, stop=n(2.2, lang), s=n(inv, lang))]) + f'<p class="wk-sub">{e(t("callsign_note", lang))}</p>')
    body += sec("rules", t("mx_rules", lang), ul([e(x) for x in lst("party_rules", lang, max=n(mx, lang), r=n(rr, lang))]))
    xp, lv = 300, (12, 15, 17)
    ex = (f'<p>{e(t("party_ex_lead", lang, xp=n(xp, lang), a=lv[0], b=lv[1], c=lv[2]))}</p><p class="eq">{e(t("party_ex_ok", lang, lo=lv[0], hi=lv[2], lim=n(max(lv) * 2 / 3, lang, 1), each=n(xp // 3, lang)))}</p>'
          f'<p>{e(t("party_ex_no", lang, a=9, b=17, lim=n(17 * 2 / 3, lang, 1)))}</p>')
    body += sec("shared-xp", t("party_xp_t", lang), f'<p>{e(t("party_xp", lang, r=n(sr, lang)))}</p><h3>{e(t("party_ex", lang))}</h3>' + ex)
    box = infobox(t("m_party", lang), '<span class="wk-icon wk-ph">⬡</span>', [(t("mx_rules", lang), f"{n(mx, lang)} max"), ("Invite", f"{n(rr, lang)} m · {n(inv, lang)} s"),
                                                                              ("Shared XP", f"{n(sr, lang)} m · 2/3")])
    body += seealso(lang, [f'<a href="experience.html">{e(t("m_experience", lang))}</a>', mlink("drones", lang, "pilot"), mlink("excavations", lang)])
    return mech(lang, "party", "party_lead", body, box)


# --- Drones --------------------------------------------------------------------------------------------------------
def drone_stats(d, lang):
    f = d["function"]
    if f == "light":
        return t("st_lamp", lang, r=n(d.get("light_radius", 10), lang))
    if f == "assault":
        return t("st_gun", lang, d=n(d.get("damage", 6), lang), m=n(d.get("max_damage", 9), lang), i=n(d.get("fire_interval", d.get("attack_interval", 1.4)), lang),
                 rg=n(d.get("range", d.get("attack_range", 9)), lang))
    if f == "scan":
        return t("st_scan", lang, sp=n(d["speed"], lang), cr=n(d["control_range"], lang), sr=n(d["scan_radius"], lang))
    return t("st_blast", lang, sp=n(d["speed"], lang), cr=n(d["control_range"], lang), br=n(d["blast_radius"], lang), d=n(d["damage"], lang), m=n(d["max_damage"], lang))


def page_drones(lang):
    body = sec("rules", t("mx_rules", lang), ul([e(x) for x in lst("dr_rules", lang, s=n(C("MIN_LAUNCH_SECONDS", 5), lang))]))
    rows = []
    order = {"light": 0, "assault": 1, "scan": 2, "kamikaze": 3}
    for it in sorted([i for i in ITEMS.values() if i.get("drone")], key=lambda i: (order.get(i["drone"]["function"], 9), i["drone"].get("energy_per_second", 0))):
        d = it["drone"]
        tech = (it.get("requirements") or {}).get("minimum_skills", {}).get("skill.tech")
        buy = min((b for _n, b, _s, _st in shop_rows_for(it["id"]) if b is not None), default=None)
        dur = d.get("duration", 0)
        rows.append([ilink(it["id"]), e(t("fn_" + d["function"], lang)), price(buy, lang), n(tech, lang) if tech else "—",
                     n(d["energy_per_second"], lang) + " E/s", f"{int(dur // 60)}:{int(dur % 60):02d}", e(drone_stats(d, lang)), n(it.get("weight", 0), lang) + " kg"])
    body += sec("table", t("dr_table", lang), table([(t("name", lang), "text"), (t("dr_fn", lang), "text"), (t("mx_price", lang), "num"), (t("dr_tech", lang), "num"),
                                                     (t("dr_drain", lang), "num"), (t("dr_flight", lang), "text"), (t("dr_stats", lang), "text"), (t("weight", lang), "num")], rows, cls="wrap-cells")
                + f'<p class="wk-sub">{e(t("dr_where", lang))} {e(t("mx_provisional", lang))}</p>')
    af, kf = C("ASSAULT_TIER_FACTOR", {"elite": 0.6, "boss": 0.35}), C("KAMIKAZE_TIER_FACTOR", {"elite": 0.45, "boss": 0.15})
    body += sec("follow", t("dr_follow_t", lang), ul([e(x) for x in lst("dr_follow", lang, m=n(C("TARGET_MEMORY", 8), lang), cap=n(C("ASSAULT_HARD_DAMAGE_CAP", 15), lang),
                                                                         el=n(af["elite"], lang), bo=n(af["boss"], lang))]))
    body += sec("pilot", t("dr_pilot_t", lang), ul([e(x) for x in lst("dr_pilot", lang, edge=pct(C("BLAST_EDGE_FACTOR", 0.4), lang), cap=n(C("KAMIKAZE_HARD_DAMAGE_CAP", 90), lang),
                                                                       el=n(kf["elite"], lang), bo=n(kf["boss"], lang))]))
    body += seealso(lang, [lk("npc.dustline_weapons_merchant"), mlink("batteries", lang), mlink("party", lang), mlink("ammunition", lang), lk("zone.relay_nine")])
    return mech(lang, "drones", "dr_lead", body)


# --- Casas ---------------------------------------------------------------------------------------------------------
def page_houses(lang):
    h = next(iter(HOUSES.values()), {})
    agent = next((npc for npc, sh in SHOPS.items() if sh.get("property")), "npc.dustline_house_agent")
    body = sec("play", t("mx_play", lang), ul([x for x in lst("ho_play", lang, agent=lk(agent))]))
    up = next(iter(h.get("upgrades", {}).values()), {"name": "261.6.66 Terminal"})
    body += sec("terminal", t("ho_terminal_t", lang), f'<p>{e(t("ho_terminal", lang, name=up["name"]))}</p><p class="wk-sub"><a href="computers.html">{e(t("m_computers", lang))}</a></p>')
    mounts = h.get("mounts", [])
    body += sec("mounts", t("ho_mounts_t", lang), f'<p>{e(t("ho_mounts", lang, n=n(len(mounts), lang)))}</p>'
                + ul([f'<span class="wk-sign">{e(m["label"])}</span>' for m in mounts]))
    prices = []
    for pr in SHOPS.get(agent, {}).get("property", []):
        name = HOUSES.get(pr["id"], {}).get("name") or next((u["name"] for hh in HOUSES.values() for k, u in hh.get("upgrades", {}).items() if k == pr["id"]), pr["id"])
        prices.append([e(name), price(pr["buy"], lang)])
    body += sec("prices", t("ho_prices", lang), table([(t("mx_item", lang), "text"), (t("mx_price", lang), "num")], prices, sortable=False) + f'<p class="note">{e(t("mx_provisional", lang))}</p>')
    rows = [(t("zone", lang), lk("zone.dustline")), (t("mx_trader", lang), lk(agent)), (t("ho_mounts_t", lang), n(len(mounts), lang)),
            ("ID", f'<code>{e(next(iter(HOUSES), ""))}</code>')]
    box = infobox(h.get("name", "House"), '<span class="wk-icon wk-ph">⌂</span>', rows)
    body += seealso(lang, [lk(agent), lk("zone.dustline"), f'<a href="computers.html">{e(t("m_computers", lang))}</a>', f'<a href="death.html">{e(t("m_death", lang))}</a>'])
    return mech(lang, "houses", "ho_lead", body, box)


# --- Excavaciones --------------------------------------------------------------------------------------------------
def page_excavations(lang):
    svc = "item.service.expedition_service"
    agent, pr = next(((npc, g["buy"]) for npc, sh in SHOPS.items() for g in sh.get("goods", []) if g["item"] == svc), ("npc.dustline_vdi_agent", 10000))
    quest = next((q["id"] for q in QUESTS if q.get("giver") == agent), None)
    body = sec("play", t("mx_play", lang), steps(lst("ex_play", lang, agent=lk(agent), price=n(pr, lang), quest=lk(quest) if quest else "—",
                                                       ahead=n(C("CALL_OUT_AHEAD", 13), lang), sp=n(C("SITE_SPACING", 36), lang), drop=n(C("DROP_SECONDS", 6), lang))))
    cmds = [[f'<code>{e(c)}</code>', e(d[lang].format(max=n(C("MAX_ROSTER", 8), lang)))] for c, d in TX["ex_cmds"]]
    body += sec("software", t("ex_soft_t", lang), table([(t("ex_cmd", lang), "text"), (t("ex_does", lang), "text")], cmds, sortable=False, cls="wrap-cells")
                + '<pre class="wk-term">vdi@drillship:~$ status\n&gt;&gt; VDI · SURFACE · ENERGY 40 / 600 · FUEL 10 / 120 L\nvdi@drillship:~$ connect 261.6.66\n… HOST CANNOT BE REACHED</pre>')
    e0, f0, ed, fd = C("START_ENERGY", 40), C("START_FUEL", 10), C("ENERGY_PER_DEPTH", 25), C("FUEL_PER_DEPTH", 6)
    txt = t("ex_res", lang, e0=n(e0, lang), f0=n(f0, lang), emax=n(C("ENERGY_MAX", 600), lang), fmax=n(C("FUEL_MAX", 120), lang),
            ed=n(ed, lang), fd=n(fd, lang), tr=n(C("TRANSIT_SECONDS", 5), lang), mx=n(C("MAX_FLOORS", 15), lang))
    crow = []
    for d in (1, 2, 3, 5, 10, int(C("MAX_FLOORS", 15))):
        cost_e, cost_f = sum(ed * k for k in range(1, d + 1)), sum(fd * k for k in range(1, d + 1))
        crow.append([f"−{d}", n(cost_e, lang), n(cost_f, lang) + " L"])
    body += sec("reserves", t("ex_res_t", lang), f"<p>{e(txt)}</p>" + f'<h3>{e(t("ex_cost", lang))}</h3>'
                + table([(t("ex_depth", lang), "text"), (t("energy", lang), "num"), (t("fuel", lang).split(" (")[0], "num")], crow, sortable=False)
                + f'<p class="wk-sub">{mlink("batteries", lang)} · <a href="fuel.html">{e(t("m_fuel", lang))}</a></p>')
    body += sec("persistence", t("mx_rules", lang), f'<p>{e(t("ex_persist", lang))}</p><p class="note">{e(t("ex_fixed", lang))} {lk("zone.excavation_c3")}</p>')
    rows = [(t("mx_trader", lang), lk(agent)), (t("mx_price", lang), price(pr, lang)), (t("quests", lang), lk(quest) if quest else ""),
            ("Roster", n(C("MAX_ROSTER", 8), lang)), (t("ex_depth", lang), f"−1 … −{n(C('MAX_FLOORS', 15), lang)}"), ("ID", f"<code>{svc}</code>")]
    box = infobox(ITEMS.get(svc, {}).get("display_name", "Expedition Service"), K.model_viewer(svc, "Expedition Service") if K.has_model(svc) else img(svc), rows)
    body += seealso(lang, [lk(svc), lk(agent), lk(quest) if quest else "", lk("zone.frontier_road_east"), mlink("party", lang), '<a href="../world.html#map">' + e(t("world_map", lang)) + "</a>"])
    return mech(lang, "excavations", "ex_lead", body, box)


# --- Contratos -----------------------------------------------------------------------------------------------------
def page_contracts(lang):
    body = sec("how", t("mx_how", lang), steps([e(x) for x in lst("co_rules", lang)])
               + '<pre class="wk-term">bank@261.6.66:~$ insert drive\n&gt;&gt; DRIVE VERIFIED. CONTRACT PAYMENT OF 800 METAL CREDITED.</pre>')
    rows = []
    for q in QUESTS:
        drives = [g["item"] for st in q.get("steps", []) for g in (st.get("grant") or {}).get("items", []) if item_cat(g["item"]) == "contract"]
        if not drives:
            continue
        job = "; ".join(st.get("objective", "") for st in q["steps"][:-1])
        if lang == "es":
            job = "; ".join(K.QUEST_ES.get(q["id"], {}).get(st["id"], st.get("objective", "")) for st in q["steps"][:-1])
        val = sum(ITEMS[d]["properties"]["drive_value"] for d in drives if d in ITEMS)
        rows.append([lk(q["id"]), lk(q["giver"]), e(job), " + ".join(lk(d) for d in drives) + f" · {n(val, lang)} Metal", n(q.get("reward", {}).get("xp", 0), lang)])
    body += sec("list", t("co_list", lang), table([(t("quest", lang), "text"), (t("co_giver", lang), "text"), (t("co_job", lang), "text"), (t("co_pays", lang), "text"),
                                                   (t("xp", lang), "num")], rows, sortable=False, cls="wrap-cells"))
    drows = [[ilink(d["id"]), n(d["properties"]["drive_value"], lang) + " Metal", n(d.get("weight", 0), lang) + " kg", n(d["properties"].get("stack_size", 1), lang)]
             for d in ITEMS.values() if item_cat(d["id"]) == "contract"]
    body += sec("drives", t("co_drives", lang), table([(t("mx_item", lang), "text"), (t("co_value", lang), "num"), (t("weight", lang), "num"), (t("stack", lang), "num")], drows, sortable=False))
    vq = next((q["id"] for q in QUESTS if q["id"] == "quest.vdi_expedition"), None)
    if vq:
        body += f'<p class="wk-note">{t("vdi_quest", lang, q=lk(vq))}</p>'
    body += seealso(lang, [f'<a href="currency.html#bank">{e(t("bank_t", lang))}</a>', f'<a href="quests.html">{e(t("quests", lang))}</a>', lk("npc.dustline_board_keeper"), mlink("excavations", lang)])
    return mech(lang, "contracts", "co_lead", body)


# --- Vehiculos (reemplaza la pagina de una sola moto, 2026-10-23) --------------------------------------------------
def page_vehicles(lang):
    shop_npc, shop = next(((k, v) for k, v in SHOPS.items() if v.get("vehicles")), (None, {}))
    vprice = {v["vehicle"]: v["buy"] for v in shop.get("vehicles", [])}
    frac = shop.get("crane", {}).get("fraction")
    keys = [("seats", lambda v: n(v["seats"], lang)), ("max_speed", lambda v: n(v["max_speed"], lang) + " m/s"),
            ("accel", lambda v: n(v["acceleration"], lang) + " m/s²"), ("decel", lambda v: n(v["deceleration"], lang) + " m/s²"),
            ("turn", lambda v: n(v["turn_rate"], lang) + " rad/s"), ("fuel", lambda v: f'{n(v["starting_fuel"], lang)} / {n(v["max_fuel"], lang)} L'),
            ("fuel_per_m", lambda v: n(v["fuel_per_meter"], lang) + " L"), ("range_start", lambda v: "≈ " + n(v["starting_fuel"] / v["fuel_per_meter"], lang) + " m"),
            ("range_full", lambda v: "≈ " + n(v["max_fuel"] / v["fuel_per_meter"], lang) + " m"), ("low_fuel", lambda v: pct(v["low_fuel_fraction"], lang)),
            ("durability", lambda v: n(v["max_durability"], lang)), ("ve_hold", lambda v: t("ve_hold_v", lang, c=n(v["cargo_cells"], lang), kg=n(v["cargo_max_kg"], lang)) if v.get("cargo_cells") else "—"),
            ("ve_price", lambda v: price(vprice.get(v["id"]), lang)),
            ("ve_crane", lambda v: price(math.ceil(vprice[v["id"]] * frac), lang) if frac and v["id"] in vprice else "—"),
            ("mount_range", lambda v: n(v["mount_range"], lang) + " m")]
    rows = [[e(t(k, lang))] + [f(v) for v in VEHICLES] for k, f in keys] + [["ID"] + [f'<code>{e(v["id"])}</code>' for v in VEHICLES]]
    body = sec("machines", t("ve_cmp", lang), table([("", "text")] + [(v["display_name"], "text") for v in VEHICLES], rows, sortable=False))
    v0 = VEH.get("vehicle.motorcycle", VEHICLES[0])
    lis = [t("v_get", lang), t("v_controls", lang, r=n(v0["mount_range"], lang)), t("v_fuel", lang, f=n(v0["fuel_per_meter"], lang), m=n(1 / v0["fuel_per_meter"], lang)),
           t("v_empty", lang, low=pct(v0["low_fuel_fraction"], lang)), t("v_rules", lang), t("v_owner", lang)]
    body += sec("rules", t("v_rules_t", lang), ul([e(x) for x in lis]))
    if shop_npc:
        bay = next((b for fl in FLOORS.values() for b in fl.get("vehicle_bays", []) if b["id"] == shop.get("bay")), {})
        body += sec("bike-shop", t("ve_shop_t", lang), f'<p>{t("ve_shop", lang, who=lk(shop_npc), spots=n(bay.get("spots", 3), lang))}</p>'
                    + ul([e(x) for x in lst("ve_shop_rules", lang, max=n(C("MAX_OWNED", 4), lang), p=pct(frac or 0.3, lang))]) + f'<p class="note">{e(t("mx_provisional", lang))}</p>')
    for v in VEHICLES:
        if v.get("cargo_cells"):
            body += sec("hold", t("ve_hold_t", lang), f'<p>{e(t("ve_hold_p", lang, name=v["display_name"], c=n(v["cargo_cells"], lang), kg=n(v["cargo_max_kg"], lang)))}</p>')
    can = ITEMS.get("item.fuel.gas_can", {})
    cap = can.get("properties", {}).get("fuel_capacity", 20)
    body += sec("refuel", t("refuel_t", lang), f'<p>{e(t("v_refuel", lang))}</p>'
                + ul([f'{lk(st["zone_id"])}: <b>{e(st["name"])}</b> · {n(st["price_per_litre"], lang)} Metal/L · '
                      + " · ".join(f'{e(v["display_name"])} ≈ {n(math.ceil(v["max_fuel"] * st["price_per_litre"]), lang)} Metal' for v in VEHICLES) for st in K.FUEL_STATIONS]
                     + [f'{lk("item.fuel.gas_can")}: {n(cap, lang)} L ≈ ' + " · ".join(f'{n(cap / v["fuel_per_meter"], lang)} m ({e(v["display_name"])})' for v in VEHICLES)])
                + f'<p><a class="btn" href="fuel.html">{e(t("m_fuel", lang))}</a></p>')
    kinds = {}
    for tr in K.REGION.get("transitions", []):
        if tr.get("from_zone") not in ZONES or ZONES[tr["from_zone"]]["status"] != "playable":
            continue
        kinds.setdefault(tr.get("presentation") or "road", []).append(tr["label"])
    for el in K.REGION.get("elevators", []):
        kinds.setdefault("elevator", []).extend(f["label"] for f in el["floors"])
    prow = [[e(t("pr_" + k, lang)), e(t("ride_yes", lang)) if K.rides_through({"presentation": k} if k != "road" else None) else e(t("ride_no", lang)),
             " ".join(f'<span class="wk-sign">{e(x)}</span>' for x in labels[:4])] for k, labels in sorted(kinds.items())]
    body += sec("passages", t("v_passages_t", lang), f'<p>{e(t("v_zone", lang))}</p><p>{e(t("v_pass_lead", lang))}</p>'
                + table([(t("passage", lang), "text"), (t("with_bike", lang), "text"), (t("examples", lang), "text")], prow, sortable=False, cls="wrap-cells"))
    body += sec("planned", t("soon", lang), ul([e(x) for x in W["v_planned"][lang]]))
    box = infobox(t("ve_shop_t", lang), '<img class="wk-icon" src="../../assets/img/concept/machine_mule.jpg" alt="" loading="lazy">',
                  [(t("mx_trader", lang), lk(shop_npc) if shop_npc else ""), (t("zone", lang), lk("zone.dustline"))]
                  + [(v["display_name"], price(vprice.get(v["id"]), lang)) for v in VEHICLES])
    body += seealso(lang, [f'<a href="fuel.html">{e(t("m_fuel", lang))}</a>', lk("item.fuel.gas_can"), lk(shop_npc) if shop_npc else "", mlink("trading", lang),
                           f'<a href="../world.html#machines">{e(t("excavators", lang))}</a>', lk("zone.frontier_road_east")])
    return K.mech_article(lang, "vehicles", t("vehicles_lead", lang), body, box)


# --- Facciones: miembros planeados (droides, 2026-10-23) ------------------------------------------------------------
PLANNED_MEMBERS = {
    "faction.rustbound": [{"en": ("Crab Droid", "A low, many-legged maintenance droid of the Pump Works; it waits for a usable model."),
                           "es": ("Crab Droid", "Un droide de mantenimiento bajo y de muchas patas de la Pump Works; espera un modelo usable.")}],
}


def faction_planned_section(fid, lang):
    items = PLANNED_MEMBERS.get(fid, [])
    if not items:
        return ""
    return sec("planned", t("planned_members", lang), ul([f'<b>{e(x[lang][0])}</b> <span class="tag tag-soon">{e(t("soon", lang))}</span> — {e(x[lang][1])}' for x in items]))


BUILDERS = {"party": page_party, "drones": page_drones, "houses": page_houses, "excavations": page_excavations, "contracts": page_contracts,
            "trading": page_trading, "food": page_food, "reading-logs": page_logs, "ammunition": page_ammo, "batteries": page_batteries,
            "vehicles": page_vehicles}
