"""GTA 6 story missions (91), for the dashboard's mission guide.

Mission names, order and chapter come from fan walkthrough lists published after launch (KeenGamer and PC Gamer,
Nov 2026). They are not an official Rockstar list, and counts differ slightly between outlets (91-93).
The one-line summaries are our own wording and stay spoiler-light (what kind of job it is, not what happens).

Each mission gets a theme. A theme links the mission to one real-world layer we can measure for the chapter's county:
  driving  -> road deaths per 100k      (car thefts, getaways, delivery and driving jobs)
  violence -> homicides per 100k        (robberies, heists, fights, weapons)
  coast    -> hurricanes per decade     (boats, diving, beach, flights over water)
  swamp    -> alligators per 10k sightings
  money    -> typical home value        (rent, real estate, banking, shopping)
  story    -> nothing to measure        (meetings, nights out, set-up scenes)
Location is the chapter's main region; the lists don't give a location for every single mission.
"""

THEMES = {
    "driving": "crash_deaths_per_100k",
    "violence": "homicide_per_100k",
    "coast": "hurricanes_per_decade",
    "swamp": "gators_per_10k_obs",
    "money": "home_value",
    "story": None,
}

# (chapter, mission name, what it is, theme)
MISSIONS = [
    # Chapter 1: Just Like Paradise (Leonida Keys)
    (1, "Prologue", "The opening: a prison storyline and a flashback to an old robbery", "violence"),
    (1, "Gone Fishing", "Pick a package out of the water, a rescue, then a flight back to the marina", "coast"),
    (1, "Gear Up", "Buy a long gun at a weapon shop", "violence"),
    (1, "Just a Scratch", "A job at a repair shop", "driving"),
    (1, "Lab Fees", "Collect rent from tenants", "money"),
    (1, "Unwanted Attention", "Head out toward the town of Hamlet", "driving"),
    (1, "Pipework", "A plumbing call tied to the rent work", "money"),
    (1, "Hey Arnold!", "Meet contacts and track down a broker", "story"),
    (1, "Island Dreams", "A diving job", "coast"),
    (1, "Feng Shui", "Move furniture", "story"),
    (1, "Coming Home", "A reunion after a prison release", "story"),
    (1, "Buck Me", "Set up banking", "money"),
    (1, "Clean Up After Donnie", "Fetch a package", "story"),
    (1, "Down to Earth", "A smuggling flight with drops over the water", "coast"),
    (1, "Clear Skies", "A job that involves a biker gang", "violence"),
    (1, "Day Release", "A night out", "story"),
    (1, "Swamped", "A meeting about a local gang, with a swampy title", "swamp"),
    (1, "Don Gone", "Search a trailer", "story"),
    (1, "Recalibration", "A meeting and some preparation", "story"),
    (1, "Tourist Trap", "A locker at a visitor centre, a run-in with crooked officers and a getaway by boat", "violence"),
    (1, "Home Sweet Home", "A story follow-up", "story"),
    (1, "Discharge Time", "A check-in that closes the chapter", "story"),
    # Chapter 2: Paradise Lost (Port Gellhorn)
    (2, "What's in the Bag?", "First jobs in Port Gellhorn", "story"),
    (2, "Ambulance Chaser", "A job driving an ambulance", "driving"),
    (2, "Just Moved In", "A shopping run", "money"),
    (2, "Girls' Trip", "An outing with a friend", "story"),
    (2, "Moses", "Meet a new contact and pick up a vehicle job", "driving"),
    (2, "Daily Driver", "Steal a car and deliver it", "driving"),
    (2, "Slam Dunk", "Get hold of painkillers", "story"),
    (2, "Breakfast Run", "A breakfast outing", "story"),
    (2, "Coffee Break", "A story conversation", "story"),
    (2, "Afternoon Delight", "Rob a strip club", "violence"),
    (2, "Checking Out", "A fight at the motel and an escape toward Vice City", "violence"),
    # Chapter 3 (Vice City)
    (3, "Welcome to Vice City", "Arrive in the city and meet a new contact", "story"),
    (3, "Dealer's Choice", "A drug deal", "story"),
    (3, "Meet the Heders", "An outing with a couple", "story"),
    (3, "Dubious Provenance", "A job at an antique store", "money"),
    (3, "Mami Knows Best", "Meet a new contact", "story"),
    (3, "South Leonida Real Estate", "Real-estate work for that contact", "money"),
    (3, "Tyrone", "Meet another contact", "story"),
    (3, "Here, Kitty Kitty", "Search for someone who's gone missing", "story"),
    (3, "Car Service", "Steal a car", "driving"),
    (3, "Top Billing", "Go to a show", "story"),
    (3, "Boobie Time", "A driving job", "driving"),
    (3, "First Impressions", "Meet a new crew", "story"),
    (3, "Caught Slipping", "Fight off a break-in", "violence"),
    (3, "Crosstown Traffic", "Tail someone across the city", "driving"),
    (3, "Credit Check", "Visit the crew's base", "story"),
    (3, "Steal the Zorrusso for Randy", "Steal a high-end car", "driving"),
    (3, "Sinfrontera National Bank", "Scout a bank", "money"),
    (3, "Security Expert", "Get ready for the bank's security", "story"),
    (3, "Ride or Die", "A job for a contact", "story"),
    (3, "Company Property", "A weapons-shipment job", "violence"),
    (3, "The Missing Link", "Work tied to illegal cockfights", "story"),
    (3, "Safe Word", "A practice run", "story"),
    (3, "Cooties", "A music-video shoot", "story"),
    (3, "Bricked Up", "A job for a contact", "story"),
    (3, "Hidden Charges", "Get explosives ready", "violence"),
    (3, "The Cartel Heist", "The bank robbery", "violence"),
    # Chapter 4: Vice City, Baby (Vice City)
    (4, "Ocean Beach", "A new base by the beach", "coast"),
    (4, "Another Life", "The chapter's opening events", "story"),
    (4, "Company Cars", "Concierge work with cars", "driving"),
    (4, "Lawyer Up", "Meet a lawyer", "story"),
    (4, "Party Hard", "Security at a celebrity event", "story"),
    (4, "Heavy Lifting", "A delivery", "driving"),
    (4, "Photo/Shoot", "A promo photo shoot", "story"),
    (4, "Making Gainz", "A fitness job", "story"),
    (4, "Watch It", "A job for a nightclub owner", "story"),
    (4, "Cash Injections", "Work for a contact", "story"),
    (4, "Amateur Hour", "Confront a director", "story"),
    (4, "Dirty Work", "Prep for the airport job", "story"),
    (4, "Too Much Baggage", "Scout the airport", "story"),
    (4, "Adventures in Babysitting", "Nightclub security", "story"),
    (4, "Fresh Evidence", "Steal blackmail material", "story"),
    (4, "Power Play", "Gather intel", "story"),
    (4, "Child's Play", "A rescue from kidnappers", "violence"),
    (4, "Headliners", "A launch party at a club", "story"),
    (4, "Close Surveillance", "Watch a target with a drone", "story"),
    (4, "Delivery Method", "An undercover job", "story"),
    (4, "Team Building", "A crew job", "story"),
    (4, "Fully Catered", "Steal a catering van", "driving"),
    (4, "VCIA Takedown", "The airport heist", "violence"),
    (4, "Sunset", "Look into what happened after", "story"),
    (4, "Starting From Zero", "The chapter's last mission", "story"),
    # Chapter 5: Top of the World, Ma (location not given in the lists; shown behind a spoiler button)
    (5, "Bird in the Hand", "Steal a vehicle", "driving"),
    (5, "Taking Liberties", "Planning", "story"),
    (5, "VC Baby", "A call for help", "story"),
    (5, "Doggie Bag", "Find contraband", "story"),
    (5, "Operation Savage Glory", "Recover a shipment", "story"),
    (5, "Protective Custody", "The final stretch", "story"),
    (5, "The End of the Road", "The final mission", "story"),
]
