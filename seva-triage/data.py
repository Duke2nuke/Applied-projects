"""Hand-written synthetic citizen grievances for seva-triage.

All 66 examples were written for this project. No real citizen data,
no scraped data, no government records. Six departments, 11 examples each.
"""

DEPARTMENTS = [
    "Water Supply",
    "Electricity",
    "Roads & Transport",
    "Health",
    "Education",
    "Revenue & Certificates",
]

DATA = [
    # --- Water Supply ---
    ("Water Supply", "There is no water supply in our street since yesterday morning."),
    ("Water Supply", "The tap water is dirty and smells bad, we cannot drink it."),
    ("Water Supply", "A water pipeline burst near the market and water is flooding the road."),
    ("Water Supply", "No water for three days in our colony, please send a water tanker."),
    ("Water Supply", "The public hand pump in our village is broken and not working."),
    ("Water Supply", "Water pressure is very low on the second floor of our building."),
    ("Water Supply", "Contaminated water is coming from the taps, children are falling sick."),
    ("Water Supply", "The overhead water tank in our area is leaking and wasting water."),
    ("Water Supply", "Our borewell has dried up and we have no drinking water."),
    ("Water Supply", "Sewage water is mixing with the drinking water supply in our lane."),
    ("Water Supply", "The municipal water tanker did not come this week as scheduled."),
    # --- Electricity ---
    ("Electricity", "There is no electricity in our house since last night."),
    ("Electricity", "Power cuts happen every evening for four hours in our area."),
    ("Electricity", "A transformer in our street has burnt out and there is no power."),
    ("Electricity", "The street light outside our house has not worked for a month."),
    ("Electricity", "My electricity bill is double this month though usage is the same."),
    ("Electricity", "Loose electric wires are hanging low over the road and are dangerous."),
    ("Electricity", "Voltage fluctuation is damaging our fridge and television."),
    ("Electricity", "The electricity meter is faulty and shows wrong readings."),
    ("Electricity", "No power supply to the water pump, so the whole village has no water."),
    ("Electricity", "The electric pole near the school is leaning and may fall."),
    ("Electricity", "I applied for a new electricity connection two months ago and it is still pending."),
    # --- Roads & Transport ---
    ("Roads & Transport", "There is a big pothole in the middle of the main road near the bus stop."),
    ("Roads & Transport", "The road in our colony is full of potholes and damaged after the rain."),
    ("Roads & Transport", "The bus service to our village was cancelled without notice."),
    ("Roads & Transport", "A fallen tree is blocking the road and traffic is stuck."),
    ("Roads & Transport", "There is no footpath on this road and children walk in traffic to school."),
    ("Roads & Transport", "The traffic signal at the main crossing has not worked for a week."),
    ("Roads & Transport", "Street vendors have blocked the road and vehicles cannot pass."),
    ("Roads & Transport", "The road outside the hospital is waterlogged after every rain."),
    ("Roads & Transport", "An accident happened at the sharp turn, we need speed breakers here."),
    ("Roads & Transport", "The bus stop shelter is broken and there is no seating for passengers."),
    ("Roads & Transport", "Heavy trucks use our residential lane at night and damage the road."),
    # --- Health ---
    ("Health", "The government hospital has no doctor available in the evening."),
    ("Health", "There is no medicine at the primary health centre for fever."),
    ("Health", "Garbage is piling up near the clinic and mosquitoes are breeding."),
    ("Health", "My mother needs an ambulance but the hospital number is not answering."),
    ("Health", "The vaccination camp in our village was cancelled without information."),
    ("Health", "Stray dogs are biting children near the health centre."),
    ("Health", "The hospital toilet is dirty and there is no clean drinking water there."),
    ("Health", "A dengue outbreak is spreading in our area and no fogging has been done."),
    ("Health", "The health centre is closed during working hours."),
    ("Health", "Patients have to wait for six hours to see a doctor at the hospital."),
    ("Health", "There is no oxygen supply at the community health centre."),
    # --- Education ---
    ("Education", "The government school in our village has no teacher for mathematics."),
    ("Education", "The school building roof is leaking and classrooms get wet in rain."),
    ("Education", "Mid-day meals are not served regularly at our school."),
    ("Education", "My daughter's scholarship has not been credited for six months."),
    ("Education", "There are no benches or desks in the primary school classrooms."),
    ("Education", "The school bus is overcrowded and unsafe for children."),
    ("Education", "The school toilet is broken and girls cannot use it."),
    ("Education", "Textbooks have not been given to students even after two months of term."),
    ("Education", "The school is closed on working days without any notice."),
    ("Education", "My son's transfer certificate is delayed by the school office."),
    ("Education", "There is no drinking water facility in the school."),
    # --- Revenue & Certificates ---
    ("Revenue & Certificates", "My income certificate application is pending for two months."),
    ("Revenue & Certificates", "I applied for a caste certificate online and it was rejected without reason."),
    ("Revenue & Certificates", "My ration card has a spelling mistake in my name."),
    ("Revenue & Certificates", "The birth certificate of my child has not been issued yet."),
    ("Revenue & Certificates", "Land records for our ancestral property show the wrong survey number."),
    ("Revenue & Certificates", "I need a domicile certificate urgently for my college admission."),
    ("Revenue & Certificates", "The property tax bill shows the wrong amount for my house."),
    ("Revenue & Certificates", "My voter ID card has the wrong address printed on it."),
    ("Revenue & Certificates", "The death certificate of my father is delayed by the municipal office."),
    ("Revenue & Certificates", "I paid the fee for a marriage certificate but have not received it."),
    ("Revenue & Certificates", "My pension application has been pending for four months."),
]


def load_data():
    """Return (texts, labels) for all synthetic grievances."""
    texts = [text for _, text in DATA]
    labels = [label for label, _ in DATA]
    return texts, labels
