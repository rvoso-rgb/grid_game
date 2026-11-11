from drafter import *
from dataclasses import dataclass


set_website_title("Grid Game")
set_site_information(
    author="Robbie Voso",
    description="See if your grid will hold up",
    sources="Thanks to the Drafter docs and my study group.",
    planning="plan.pdf",
    links=["https://github.com/rvoso-rgb/grid_game"]
)
hide_debug_information()
set_website_framed(False)


# ---------------------------------------------------------------
# Global constants (allowed). Tune these to change game balance.
# ---------------------------------------------------------------
FINAL_YEAR = 10
START_BUDGET = 600
INCOME_NORMAL = 300
INCOME_HARD = 250

GROWTH_NORMAL = 0.05      # demand grows 5 percent per year
GROWTH_HARD = 0.08
DATA_CENTER_MW = 40       # flat load added per year after year 1

EMISSIONS_START = 30000   # tons of CO2 allowed on the test day in year 1
EMISSIONS_STEP = 2500     # target drops by this much each year
HARD_EMISSIONS_STEP = 3000

EVENTS = ["Heat wave", "Plant outage"]   # both worst days are tested every year
FIRM_KINDS = ["Coal", "Gas", "Nuclear"]  # plants that can suffer an outage

BASE_DEMAND = [600, 570, 550, 540, 545, 580, 650, 740, 800, 830, 850, 860,
               870, 880, 890, 900, 930, 980, 1000, 980, 920, 820, 720, 650]

SOLAR_PROFILE = [0, 0, 0, 0, 0, 0.05, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0,
                 1.0, 0.9, 0.8, 0.6, 0.4, 0.2, 0.05, 0, 0, 0, 0, 0]
WIND_PROFILE = [0.5, 0.6, 0.6, 0.5, 0.4, 0.4, 0.3, 0.3, 0.2, 0.2, 0.2, 0.2,
                0.25, 0.3, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.7, 0.6, 0.6, 0.5]
FLAT_PROFILE = [1.0] * 24

# capacity in MW, cost in millions, build time in years,
# emissions in tons of CO2 per MWh, and the hourly availability profile
PLANT_TYPES = {
    "Coal": {"capacity": 300, "cost": 150, "build": 1, "emissions": 0.9, "profile": FLAT_PROFILE},
    "Gas": {"capacity": 250, "cost": 120, "build": 1, "emissions": 0.4, "profile": FLAT_PROFILE},
    "Solar": {"capacity": 200, "cost": 100, "build": 1, "emissions": 0.0, "profile": SOLAR_PROFILE},
    "Wind": {"capacity": 250, "cost": 130, "build": 2, "emissions": 0.0, "profile": WIND_PROFILE},
    "Nuclear": {"capacity": 500, "cost": 400, "build": 3, "emissions": 0.0, "profile": FLAT_PROFILE},
}


# ---------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------
@dataclass
class Plant:
    kind: str
    capacity_mw: int
    cost: int
    online_year: int


@dataclass
class State:
    player_name: str
    year: int
    budget: int
    plants: list[Plant]
    hard_mode: bool
    shortfall_hours: int
    emissions: int
    event: str
    message: str


# ---------------------------------------------------------------
# Helper functions (not routes)
# ---------------------------------------------------------------
def starting_plants() -> list[Plant]:
    """The grid the player begins with. All of it is online in year 1."""
    plants = []
    for _ in range(4):
        plants.append(Plant("Coal", 300, 150, 1))
    plants.append(Plant("Gas", 250, 120, 1))
    return plants


def make_demand(year: int, event: str, hard_mode: bool) -> list[int]:
    """Build the 24 hour demand list for one test day."""
    growth = GROWTH_HARD if hard_mode else GROWTH_NORMAL
    demand = []
    for hour in range(24):
        value = BASE_DEMAND[hour] * (1 + growth * (year - 1))
        value += DATA_CENTER_MW * (year - 1)
        if event == "Heat wave" and 12 <= hour <= 20:
            value = value * 1.2
        demand.append(round(value))
    return demand


def emissions_target(state: State) -> int:
    step = HARD_EMISSIONS_STEP if state.hard_mode else EMISSIONS_STEP
    return EMISSIONS_START - step * (state.year - 1)


def largest_firm_plant(plants: list[Plant], year: int):
    """Find the biggest online firm plant. The outage event takes it offline."""
    biggest = None
    for plant in plants:
        if plant.online_year <= year and plant.kind in FIRM_KINDS:
            if biggest is None or plant.capacity_mw > biggest.capacity_mw:
                biggest = plant
    return biggest


def simulate_day(plants: list[Plant], year: int, event: str, hard_mode: bool):
    """Run one test day. Returns demand, supply, total emissions, and shortfall hours."""
    demand = make_demand(year, event, hard_mode)
    supply = [0.0] * 24
    emissions = 0.0

    failed_plant = None
    if event == "Plant outage":
        failed_plant = largest_firm_plant(plants, year)

    # Main loop over the list of Plant instances in State
    for plant in plants:
        if plant.online_year > year:
            continue  # still under construction, so it adds nothing today
        if plant is failed_plant:
            continue  # knocked out by the outage event
        info = PLANT_TYPES[plant.kind]
        for hour in range(24):
            output = plant.capacity_mw * info["profile"][hour]
            supply[hour] += output
            emissions += output * info["emissions"]

    shortfall = 0
    for hour in range(24):
        if supply[hour] < demand[hour]:
            shortfall += 1
    return demand, supply, round(emissions), shortfall


def plant_lines(state: State):
    """Split the plants into online lines and under construction lines."""
    online = []
    building = []
    for plant in state.plants:
        if plant.online_year <= state.year:
            online.append(f"{plant.kind}, {plant.capacity_mw} MW")
        else:
            building.append(f"{plant.kind}, {plant.capacity_mw} MW, online in year {plant.online_year}")
    return online, building


def hour_table(state: State):
    """Hour by hour table for the worst day of the year."""
    demand, supply, emissions, shortfall = simulate_day(
        state.plants, state.year, state.event, state.hard_mode)
    rows = [["Hour", "Demand MW", "Supply MW", "Status"]]
    for hour in range(24):
        status = "SHORT" if supply[hour] < demand[hour] else "ok"
        rows.append([str(hour), str(demand[hour]), str(round(supply[hour])), status])
    return Table(rows)


# ---------------------------------------------------------------
# Routes and pages
# ---------------------------------------------------------------
@route
def index(state: State) -> Page:
    return Page(state, [
        Header("Keep the Grid On"),
        Text("You run a regional grid for 10 years. Each year you are tested against two worst case days. "
             "Your grid must cover demand every hour and stay under the emissions target."),
        Text("Data centers keep adding load, so build ahead. Nuclear and wind take longer to build."),
        Text("Your name"),
        TextBox("player_name", state.player_name),
        CheckBox("hard_mode", state.hard_mode),
        Text("Hard mode (faster demand growth, tougher targets, less income)"),
        Button("Start game", start_game),
        Button("How it works", how_it_works),
    ])


@route
def how_it_works(state: State) -> Page:
    lines = []
    for kind in PLANT_TYPES:
        info = PLANT_TYPES[kind]
        lines.append(f"{kind} gives {info['capacity']} MW, costs {info['cost']}M, "
                     f"takes {info['build']} year(s), and emits {info['emissions']} tons per MWh.")
    return Page(state, [
        Header("How it works"),
        Text("Solar only produces during the day and wind is uneven. Coal, gas, and nuclear run all day."),
        Text("Each test day has a heat wave or a plant outage that removes your largest firm plant."),
        BulletedList(lines),
        Button("Back to home", index),
    ])


@route
def start_game(state: State, player_name: str, hard_mode: bool) -> Page:
    if player_name.strip() == "":
        state.player_name = "Operator"
    else:
        state.player_name = player_name.strip()
    state.hard_mode = hard_mode
    state.year = 1
    state.budget = START_BUDGET
    state.plants = starting_plants()
    state.shortfall_hours = 0
    state.emissions = 0
    state.event = EVENTS[0]
    state.message = ""
    return build_menu(state)


@route
def build_menu(state: State) -> Page:
    online, building = plant_lines(state)
    content = [
        Header(f"Year {state.year} of {FINAL_YEAR}"),
        Text(f"Budget, {state.budget}M. Emissions target for this year, {emissions_target(state)} tons."),
    ]
    if state.message != "":
        content.append(Text(state.message))

    content.append(Header("Online now", 2))
    if len(online) > 0:
        content.append(BulletedList(online))
    else:
        content.append(Text("Nothing online."))

    content.append(Header("Under construction", 2))
    if len(building) > 0:
        content.append(BulletedList(building))
    else:
        content.append(Text("Nothing under construction."))

    content.append(Header("Build", 2))
    content.append(SelectBox("kind", list(PLANT_TYPES.keys()), "Gas"))
    content.append(TextBox("quantity", "1"))
    content.append(Button("Build", buy_plant))

    content.append(Header("Retire a plant", 2))
    content.append(SelectBox("retire_kind", list(PLANT_TYPES.keys()), "Coal"))
    content.append(Button("Retire one online plant of this type", retire_plant))

    content.append(Header("Ready", 2))
    content.append(Button("Run this year's test days", run_year))
    content.append(Button("How it works", how_it_works))
    return Page(state, content)


@route
def buy_plant(state: State, kind: str, quantity: str) -> Page:
    info = PLANT_TYPES[kind]
    text = quantity.strip()

    if not text.isdigit() or int(text) == 0:
        state.message = "Enter a whole number greater than zero."
        return purchase_error(state)
    elif info["cost"] * int(text) > state.budget:
        state.message = f"{text} {kind} plant(s) cost {info['cost'] * int(text)}M and you have {state.budget}M."
        return purchase_error(state)
    else:
        count = int(text)
        for _ in range(count):
            state.plants.append(Plant(kind, info["capacity"], info["cost"], state.year + info["build"]))
        state.budget -= info["cost"] * count
        state.message = f"Started {count} {kind} plant(s). They come online in year {state.year + info['build']}."
        return build_menu(state)


@route
def purchase_error(state: State) -> Page:
    return Page(state, [
        Header("Purchase failed"),
        Text(state.message),
        Button("Back to build menu", build_menu),
    ])


@route
def retire_plant(state: State, retire_kind: str) -> Page:
    found = False
    for plant in state.plants:
        if plant.kind == retire_kind and plant.online_year <= state.year:
            state.plants.remove(plant)
            found = True
            break  # stop right after removing so the list is never changed mid loop
    if found:
        state.message = f"Retired one {retire_kind} plant."
    else:
        state.message = f"You have no online {retire_kind} plants to retire."
    return build_menu(state)


@route
def run_year(state: State) -> Page:
    worst_shortfall = -1
    worst_emissions = 0

    for event in EVENTS:
        demand, supply, emissions, shortfall = simulate_day(
            state.plants, state.year, event, state.hard_mode)
        if shortfall > worst_shortfall:
            worst_shortfall = shortfall
            state.event = event  # remember the worse day for the table
        if emissions > worst_emissions:
            worst_emissions = emissions

    state.shortfall_hours = worst_shortfall
    state.emissions = worst_emissions
    target = emissions_target(state)

    if state.shortfall_hours > 0:
        state.message = f"Blackout during the {state.event.lower()}. Demand beat supply for {state.shortfall_hours} hour(s)."
        return game_over(state)
    elif state.emissions > target:
        state.message = f"The grid held but emitted {state.emissions} tons against a target of {target}."
        return game_over(state)
    elif state.year >= FINAL_YEAR:
        return victory(state)
    else:
        return year_results(state)


@route
def year_results(state: State) -> Page:
    return Page(state, [
        Header(f"Year {state.year} cleared"),
        Text(f"Reliability, passed on both test days."),
        Text(f"Emissions, {state.emissions} tons against a target of {emissions_target(state)}."),
        Button(f"Advance to year {state.year + 1}", advance_year),
    ])


@route
def advance_year(state: State) -> Page:
    state.year += 1
    if state.hard_mode:
        state.budget += INCOME_HARD
    else:
        state.budget += INCOME_NORMAL

    # Loop over the plants to announce anything that just finished building
    finished = []
    for plant in state.plants:
        if plant.online_year == state.year:
            finished.append(plant.kind)
    if len(finished) > 0:
        state.message = "Now online, " + ", ".join(finished) + "."
    else:
        state.message = "No new plants came online this year."
    return build_menu(state)


@route
def game_over(state: State) -> Page:
    return Page(state, [
        Header("Game over"),
        Text(f"{state.player_name}, you fell in year {state.year}."),
        Text(state.message),
        Text(f"Worst day, {state.event}."),
        hour_table(state),
        Button("Play again", index),
    ])


@route
def victory(state: State) -> Page:
    online, building = plant_lines(state)
    return Page(state, [
        Header("You kept the lights on"),
        Text(f"{state.player_name}, you cleared all {FINAL_YEAR} years."),
        Text("Your final grid"),
        BulletedList(online),
        Button("Play again", index),
    ])


start_server(State("Operator", 1, START_BUDGET, [], False, 0, 0, EVENTS[0], ""))
