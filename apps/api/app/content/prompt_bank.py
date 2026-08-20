"""Original IELTS-style writing and speaking papers.

These are practice materials written for Northband. They are not copied from
Cambridge, British Council, or IDP papers.
"""

from __future__ import annotations

from typing import Any

PROMPT_BANK_VERSION = 1

T2_INSTRUCTION = (
    "Give reasons for your answer and include any relevant examples from your own knowledge or experience."
)
T1_AC_INSTRUCTION = (
    "Summarise the information by selecting and reporting the main features, and make comparisons where relevant."
)
SPEAK_P2_EXAMINER = (
    "Now, I'm going to give you a topic and I'd like you to talk about it for one to two minutes. "
    "Before you talk, you will have one minute to think about what you are going to say. "
    "You can make some notes if you wish. Do you understand?"
)
SPEAK_P1_EXAMINER = "Now, in this first part, I'd like to ask you some questions about yourself."

TEAL = "#1b4d4a"
GOLD = "#8a6328"
SLATE = "#3d6b7a"


def _visual(
    *,
    vid: str,
    kind: str,
    title: str,
    x_key: str,
    series: list[dict[str, str]],
    rows: list[dict[str, Any]],
    y_label: str | None = None,
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "id": vid,
        "kind": kind,
        "title": title,
        "xKey": x_key,
        "series": series,
        "rows": rows,
    }
    if y_label:
        spec["yLabel"] = y_label
    return spec


def format_writing_prompt(
    *,
    topic: str,
    instruction: str = "",
    bullets: list[str] | None = None,
    bullet_lead: str = "",
) -> str:
    parts = [topic.strip()]
    if instruction:
        parts.append(instruction.strip())
    if bullets:
        lead = bullet_lead or "In your letter:"
        parts.append("\n".join([lead, *[f"- {item}" for item in bullets]]))
    return "\n\n".join(parts)


def format_speaking_prompt(part: str, pack: dict[str, Any]) -> str:
    if part == "part1":
        p1 = pack["part1"]
        return "\n".join([p1["topic"], *[f"- {q}" for q in p1["questions"]]])
    if part == "part2":
        p2 = pack["part2"]
        return "\n".join(
            [
                p2["topic"],
                "You should say:",
                *[f"- {item}" for item in p2["bullets"]],
                f"- and explain {p2['explain']}",
            ]
        )
    if part == "full":
        return "\n\n".join(
            [
                "Part 1 — Interview",
                format_speaking_prompt("part1", pack),
                "Part 2 — Long turn",
                format_speaking_prompt("part2", pack),
                "Part 3 — Discussion",
                format_speaking_prompt("part3", pack),
            ]
        )
    return "\n".join([f"- {q}" for q in pack["part3"]["questions"]])


def _writing(
    slug: str,
    module: str,
    task: str,
    title: str,
    topic: str,
    instruction: str = "",
    bullets: list[str] | None = None,
    bullet_lead: str = "",
    visual: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "skill": "writing",
        "module": module,
        "task": task,
        "title": title,
        "prompt": format_writing_prompt(
            topic=topic, instruction=instruction, bullets=bullets, bullet_lead=bullet_lead
        ),
        "payload": {"visual": visual} if visual else {},
    }


def _speaking(slug: str, title: str, pack: dict[str, Any]) -> dict[str, Any]:
    pack = {**pack, "id": slug, "title": title}
    return {
        "slug": slug,
        "skill": "speaking",
        "module": "shared",
        "task": "pack",
        "title": title,
        "prompt": format_speaking_prompt("full", pack),
        "payload": {"speaking": pack},
    }


CURATED_WRITING: list[dict[str, Any]] = [
    _writing(
        "w-ac-t1-households",
        "academic",
        "task1",
        "Households owned vs rented",
        "The chart below shows the percentage of households in owned and rented accommodation in England and Wales between 1918 and 2011.",
        T1_AC_INSTRUCTION,
        visual=_visual(
            vid="households-ew",
            kind="line",
            title="Households in owned and rented accommodation, England and Wales, 1918–2011",
            y_label="Percentage of households",
            x_key="year",
            series=[
                {"key": "Owned", "label": "Owned", "color": TEAL},
                {"key": "Rented", "label": "Rented", "color": GOLD},
            ],
            rows=[
                {"year": "1918", "Owned": 23, "Rented": 77},
                {"year": "1939", "Owned": 32, "Rented": 68},
                {"year": "1953", "Owned": 32, "Rented": 68},
                {"year": "1961", "Owned": 42, "Rented": 58},
                {"year": "1971", "Owned": 50, "Rented": 50},
                {"year": "1981", "Owned": 58, "Rented": 42},
                {"year": "1991", "Owned": 67, "Rented": 33},
                {"year": "2001", "Owned": 69, "Rented": 31},
                {"year": "2011", "Owned": 64, "Rented": 36},
            ],
        ),
    ),
    _writing(
        "w-ac-t1-energy-mix",
        "academic",
        "task1",
        "Energy by source, 2000 and 2020",
        "The charts below show the proportion of energy produced from coal, gas, nuclear and renewables in a European country in 2000 and 2020.",
        T1_AC_INSTRUCTION,
        visual=_visual(
            vid="energy-mix-2000-2020",
            kind="bar",
            title="Energy produced by source in a European country, 2000 and 2020",
            y_label="Percentage of total energy produced",
            x_key="source",
            series=[
                {"key": "y2000", "label": "2000", "color": TEAL},
                {"key": "y2020", "label": "2020", "color": GOLD},
            ],
            rows=[
                {"source": "Coal", "y2000": 42, "y2020": 18},
                {"source": "Gas", "y2000": 28, "y2020": 31},
                {"source": "Nuclear", "y2000": 22, "y2020": 21},
                {"source": "Renewables", "y2000": 8, "y2020": 30},
            ],
        ),
    ),
    _writing(
        "w-ac-t1-internet",
        "academic",
        "task1",
        "Internet users 2000–2020",
        "The graph below shows internet users as a percentage of the population in three countries between 2000 and 2020.",
        T1_AC_INSTRUCTION,
        visual=_visual(
            vid="internet-users",
            kind="line",
            title="Internet users as a percentage of the population, 2000–2020",
            y_label="Percentage of population",
            x_key="year",
            series=[
                {"key": "UK", "label": "UK", "color": TEAL},
                {"key": "USA", "label": "USA", "color": GOLD},
                {"key": "China", "label": "China", "color": SLATE},
            ],
            rows=[
                {"year": "2000", "UK": 27, "USA": 43, "China": 2},
                {"year": "2005", "UK": 70, "USA": 68, "China": 9},
                {"year": "2010", "UK": 85, "USA": 72, "China": 34},
                {"year": "2015", "UK": 92, "USA": 75, "China": 50},
                {"year": "2020", "UK": 95, "USA": 89, "China": 70},
            ],
        ),
    ),
    _writing(
        "w-ac-t1-library",
        "academic",
        "task1",
        "Reasons for library visits",
        "The chart below shows reasons for visiting a public library in a survey of 1,000 adults.",
        T1_AC_INSTRUCTION,
        visual=_visual(
            vid="library-visits",
            kind="pie",
            title="Reasons for visiting a public library (survey of 1,000 adults)",
            x_key="reason",
            series=[{"key": "Percent", "label": "Percent", "color": TEAL}],
            rows=[
                {"reason": "Borrow books", "Percent": 38},
                {"reason": "Study / work", "Percent": 24},
                {"reason": "Use computers", "Percent": 18},
                {"reason": "Children’s activities", "Percent": 12},
                {"reason": "Other", "Percent": 8},
            ],
        ),
    ),
    _writing(
        "w-ac-t1-energy-sector",
        "academic",
        "task1",
        "Energy use by sector",
        "The chart below shows the share of energy use by sector in 2020.",
        T1_AC_INSTRUCTION,
        visual=_visual(
            vid="energy-2020",
            kind="bar",
            title="Share of energy use by sector, 2020",
            y_label="Percentage of total energy use",
            x_key="sector",
            series=[{"key": "Share", "label": "Share", "color": TEAL}],
            rows=[
                {"sector": "Transport", "Share": 29},
                {"sector": "Industry", "Share": 25},
                {"sector": "Residential", "Share": 22},
                {"sector": "Commercial", "Share": 15},
                {"sector": "Agriculture & other", "Share": 9},
            ],
        ),
    ),
    _writing(
        "w-ac-t1-commute",
        "academic",
        "task1",
        "How people travelled to work",
        "The graph below shows how people in a city travelled to work in 1990, 2005 and 2020.",
        T1_AC_INSTRUCTION,
        visual=_visual(
            vid="commute-modes",
            kind="bar",
            title="Main mode of travel to work in a city, 1990–2020",
            y_label="Percentage of workers",
            x_key="mode",
            series=[
                {"key": "y1990", "label": "1990", "color": TEAL},
                {"key": "y2005", "label": "2005", "color": GOLD},
                {"key": "y2020", "label": "2020", "color": SLATE},
            ],
            rows=[
                {"mode": "Car", "y1990": 62, "y2005": 58, "y2020": 44},
                {"mode": "Bus", "y1990": 18, "y2005": 16, "y2020": 14},
                {"mode": "Rail", "y1990": 9, "y2005": 12, "y2020": 18},
                {"mode": "Cycle / walk", "y1990": 8, "y2005": 10, "y2020": 16},
                {"mode": "Work from home", "y1990": 3, "y2005": 4, "y2020": 8},
            ],
        ),
    ),
    _writing(
        "w-ac-t1-enrolment",
        "academic",
        "task1",
        "University enrolment by field",
        "The chart below shows university enrolment by field of study in a country in 2010 and 2022.",
        T1_AC_INSTRUCTION,
        visual=_visual(
            vid="uni-enrolment",
            kind="bar",
            title="University enrolment by field, 2010 and 2022",
            y_label="Percentage of students",
            x_key="field",
            series=[
                {"key": "y2010", "label": "2010", "color": TEAL},
                {"key": "y2022", "label": "2022", "color": GOLD},
            ],
            rows=[
                {"field": "Business", "y2010": 28, "y2022": 24},
                {"field": "STEM", "y2010": 22, "y2022": 31},
                {"field": "Health", "y2010": 14, "y2022": 18},
                {"field": "Arts & humanities", "y2010": 21, "y2022": 15},
                {"field": "Education", "y2010": 15, "y2022": 12},
            ],
        ),
    ),
    _writing(
        "w-ac-t1-water",
        "academic",
        "task1",
        "Freshwater use",
        "The chart below shows how freshwater was used in a country in 2021.",
        T1_AC_INSTRUCTION,
        visual=_visual(
            vid="water-use",
            kind="pie",
            title="Freshwater use by sector, 2021",
            x_key="sector",
            series=[{"key": "Percent", "label": "Percent", "color": TEAL}],
            rows=[
                {"sector": "Agriculture", "Percent": 54},
                {"sector": "Industry", "Percent": 22},
                {"sector": "Households", "Percent": 16},
                {"sector": "Energy", "Percent": 5},
                {"sector": "Other", "Percent": 3},
            ],
        ),
    ),
    _writing(
        "w-ac-t2-community-service",
        "academic",
        "task2",
        "Compulsory community service",
        "Some people believe that unpaid community service should be a compulsory part of high school programmes. To what extent do you agree or disagree?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-university-purpose",
        "academic",
        "task2",
        "Purpose of university",
        "Some people think universities should provide graduates with the knowledge and skills needed in the workplace. Others think the true function of a university is to give access to knowledge for its own sake. Discuss both views and give your opinion.",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-prison",
        "academic",
        "task2",
        "Prison vs other ways to cut crime",
        "Some people think the best way to reduce crime is to give longer prison sentences. Others believe there are better ways. Discuss both views and give your opinion.",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-technology-children",
        "academic",
        "task2",
        "Technology in childhood",
        "Nowadays children spend a large amount of time using phones and computers. Do the advantages of this outweigh the disadvantages?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-remote-work",
        "academic",
        "task2",
        "Working from home",
        "More people are choosing to work from home rather than in an office. Is this a positive or negative development?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-advertising",
        "academic",
        "task2",
        "Advertising and consumer choice",
        "Some people say that advertising encourages us to buy things we do not need. Others say it is useful because it informs us about new products. Discuss both views and give your opinion.",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-gap-year",
        "academic",
        "task2",
        "Gap years",
        "In some countries, young people take a year off between school and university. What are the advantages and disadvantages of this?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-public-transport",
        "academic",
        "task2",
        "Cars vs public transport",
        "Governments should spend more money on public transport and less on roads for private cars. To what extent do you agree or disagree?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-international-news",
        "academic",
        "task2",
        "Local vs international news",
        "Some people believe that international news is of little interest to ordinary people. Others think it is essential. Discuss both views and give your opinion.",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-art-funding",
        "academic",
        "task2",
        "Public funding for the arts",
        "Some people think governments should fund artists and musicians. Others think this money should be spent on more important things. Discuss both views and give your own opinion.",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-online-learning",
        "academic",
        "task2",
        "Online courses vs campus study",
        "Online education is becoming more popular than studying on a university campus. Do you think this is a positive or negative development?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-ac-t2-animal-testing",
        "academic",
        "task2",
        "Animals in scientific research",
        "Some people think it is acceptable to use animals in scientific research. Others believe it is never justified. Discuss both views and give your opinion.",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-gt-t1-hotel",
        "general",
        "task1",
        "Letter about a hotel stay",
        "You recently stayed in a hotel and had several problems with the room and service. Write a letter to the hotel manager.",
        bullets=["describe the problems", "explain how they affected your stay", "say what you would like the manager to do"],
        bullet_lead="In your letter:",
    ),
    _writing(
        "w-gt-t1-neighbour",
        "general",
        "task1",
        "Noise from a neighbour",
        "You have a neighbour who plays loud music late at night. Write a letter to your neighbour.",
        bullets=["explain the problem", "say how it is affecting you", "suggest what they could do"],
        bullet_lead="In your letter:",
    ),
    _writing(
        "w-gt-t1-course",
        "general",
        "task1",
        "Enquiry about an evening course",
        "You want to join an evening course at a local college. Write a letter to the college.",
        bullets=["say which course you are interested in", "ask about times, fees and entry requirements", "explain why you want to take the course"],
        bullet_lead="In your letter:",
    ),
    _writing(
        "w-gt-t1-job-thanks",
        "general",
        "task1",
        "Thank a manager after work experience",
        "You recently completed two weeks of unpaid work experience. Write a letter to the manager.",
        bullets=["thank them for the opportunity", "describe what you learned", "say how you hope to use this experience in the future"],
        bullet_lead="In your letter:",
    ),
    _writing(
        "w-gt-t1-lost-item",
        "general",
        "task1",
        "Lost bag on a train",
        "You left a bag on a train. Write a letter to the lost property office.",
        bullets=["describe the bag and its contents", "say where and when you left it", "explain how the office can contact you"],
        bullet_lead="In your letter:",
    ),
    _writing(
        "w-gt-t1-complaint-shop",
        "general",
        "task1",
        "Faulty item from an online shop",
        "You bought an item online and it arrived damaged. Write a letter to the company.",
        bullets=["describe the item and the problem", "explain what you have already done", "say what you want the company to do"],
        bullet_lead="In your letter:",
    ),
    _writing(
        "w-gt-t1-invitation",
        "general",
        "task1",
        "Invite a friend to visit",
        "A friend from another country is planning to visit your town. Write a letter to your friend.",
        bullets=["suggest when they should come", "describe two places you could visit together", "explain what they should bring"],
        bullet_lead="In your letter:",
    ),
    _writing(
        "w-gt-t1-landlord",
        "general",
        "task1",
        "Repair request to a landlord",
        "There is a problem with the heating in your rented flat. Write a letter to the landlord.",
        bullets=["describe the problem", "explain how it is affecting you", "say what you would like the landlord to do and by when"],
        bullet_lead="In your letter:",
    ),
    _writing(
        "w-gt-t2-living-longer",
        "general",
        "task2",
        "People living longer",
        "In many countries, people are living longer. What problems does this cause for individuals and society? What measures could be taken to address these problems?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-gt-t2-fast-food",
        "general",
        "task2",
        "Fast food and health",
        "Fast food is becoming more popular, and this is having a negative effect on health. What are the causes of this, and what solutions can you suggest?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-gt-t2-city-vs-country",
        "general",
        "task2",
        "City or countryside",
        "Some people prefer to live in a city. Others prefer the countryside. Discuss both views and give your own opinion.",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-gt-t2-shopping-online",
        "general",
        "task2",
        "Shopping online",
        "More people now shop online instead of going to local shops. Do the advantages of this outweigh the disadvantages?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-gt-t2-volunteer",
        "general",
        "task2",
        "Volunteering",
        "Some people think everyone should do unpaid volunteer work in their free time. To what extent do you agree or disagree?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-gt-t2-phones-meals",
        "general",
        "task2",
        "Phones at mealtimes",
        "Many families now use phones at mealtimes instead of talking to each other. Why is this happening, and what can be done about it?",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-gt-t2-job-satisfaction",
        "general",
        "task2",
        "Job satisfaction vs high salary",
        "Some people think job satisfaction is more important than a high salary. Others disagree. Discuss both views and give your opinion.",
        T2_INSTRUCTION,
    ),
    _writing(
        "w-gt-t2-tourism",
        "general",
        "task2",
        "Tourism in small towns",
        "Tourism is growing in many small towns. What problems can this cause, and how can they be solved?",
        T2_INSTRUCTION,
    ),
]


def _pack(
    part1_topic: str,
    part1_qs: list[str],
    part2_topic: str,
    part2_bullets: list[str],
    part2_explain: str,
    part3_qs: list[str],
    part3_lead: str,
) -> dict[str, Any]:
    return {
        "part1": {"topic": part1_topic, "examiner": SPEAK_P1_EXAMINER, "questions": part1_qs},
        "part2": {
            "topic": part2_topic,
            "examiner": SPEAK_P2_EXAMINER,
            "bullets": part2_bullets,
            "explain": part2_explain,
        },
        "part3": {
            "examiner": part3_lead,
            "questions": part3_qs,
        },
    }


CURATED_SPEAKING: list[dict[str, Any]] = [
    _speaking(
        "s-hometown-skill",
        "Hometown / learning a skill",
        _pack(
            "Let's talk about your hometown.",
            [
                "Where is your hometown?",
                "What do you like most about living there?",
                "Has your hometown changed much in recent years?",
                "Would you like to continue living there in the future?",
            ],
            "Describe a skill you would like to learn.",
            ["what the skill is", "why you want to learn it", "how you would learn it"],
            "how this skill would help you",
            [
                "Do you think schools should spend more time teaching practical skills? Why or why not?",
                "What skills do you think will be most useful in the future?",
                "Is it better to learn a new skill from a teacher or by yourself?",
                "Some people say we should keep learning throughout our lives. Do you agree?",
            ],
            "We've been talking about learning a skill, and I'd like to discuss with you one or two more general questions related to this.",
        ),
    ),
    _speaking(
        "s-freetime-place",
        "Free time / a place to visit",
        _pack(
            "Let's talk about what you do in your free time.",
            [
                "What do you usually do in your free time?",
                "Did you have the same hobbies when you were a child?",
                "Do you prefer to spend free time alone or with other people?",
                "Is there a new hobby you would like to try?",
            ],
            "Describe a place you would like to visit.",
            ["where it is", "how you would get there", "what you would do there"],
            "why you would like to visit this place",
            [
                "Why do you think people enjoy travelling to other countries?",
                "What are the advantages and disadvantages of tourism for a local area?",
                "Do you think it is better to travel independently or on an organised tour?",
                "How might travel change in the next twenty years?",
            ],
            "We've been talking about a place you would like to visit, and I'd like to discuss with you one or two more general questions related to this.",
        ),
    ),
    _speaking(
        "s-work-helper",
        "Work or study / a helpful person",
        _pack(
            "Let's talk about your work or studies.",
            [
                "Do you work or are you a student?",
                "What do you enjoy most about that?",
                "What is the most difficult part of your work or studies?",
                "What would you like to do in the future?",
            ],
            "Describe a person who has helped you in an important way.",
            ["who this person is", "how they helped you", "when this happened"],
            "why this help was important to you",
            [
                "Do you think people are less willing to help others than in the past?",
                "Should helping others be taught in schools?",
                "What are the advantages of volunteering in the community?",
                "Some people prefer to solve problems alone. Is that a good approach?",
            ],
            "We've been talking about a person who helped you, and I'd like to discuss with you one or two more general questions related to this.",
        ),
    ),
    _speaking(
        "s-news-book",
        "Daily news / an interesting book",
        _pack(
            "Let's talk about news and the media.",
            [
                "How do you usually get the news?",
                "Do you prefer reading the news or watching it?",
                "Is there too much news in daily life?",
                "Did you follow the news when you were younger?",
            ],
            "Describe a book that you found interesting.",
            ["what the book was", "when you read it", "what it was about"],
            "why you found it interesting",
            [
                "Do you think people read less than they used to? Why?",
                "Should children be encouraged to read more paper books than screens?",
                "What makes a book become a classic?",
                "How might reading habits change in the next twenty years?",
            ],
            "We've been talking about a book you found interesting, and I'd like to discuss with you one or two more general questions related to this.",
        ),
    ),
    _speaking(
        "s-food-meal",
        "Food / a memorable meal",
        _pack(
            "Let's talk about food and cooking.",
            [
                "What kinds of food do you like to eat?",
                "Do you prefer eating at home or in a restaurant?",
                "Did you help with cooking when you were a child?",
                "Is there a dish you would like to learn to cook?",
            ],
            "Describe a memorable meal you have had.",
            ["where you had it", "who you were with", "what you ate"],
            "why this meal was memorable",
            [
                "Why do you think people enjoy eating together?",
                "Has the way people eat changed in your country?",
                "Should schools teach children how to cook?",
                "What are the advantages and disadvantages of eating in restaurants?",
            ],
            "We've been talking about a meal you remember, and I'd like to discuss with you one or two more general questions related to this.",
        ),
    ),
    _speaking(
        "s-home-neighbour",
        "Where you live / a neighbour",
        _pack(
            "Let's talk about your home.",
            [
                "Do you live in a house or an apartment?",
                "What is your favourite room, and why?",
                "Would you like to change anything about your home?",
                "Do you prefer living in a quiet or a busy area?",
            ],
            "Describe a neighbour you know.",
            ["who they are", "how you know them", "what they are like"],
            "how you feel about having this person as a neighbour",
            [
                "Do you think it is important to know your neighbours?",
                "How have neighbourhoods changed compared with the past?",
                "What makes a community a good place to live?",
                "Should cities design more shared spaces for residents?",
            ],
            "We've been talking about neighbours, and I'd like to discuss with you one or two more general questions related to this.",
        ),
    ),
    _speaking(
        "s-sport-event",
        "Sport / a public event",
        _pack(
            "Let's talk about sport and exercise.",
            [
                "Do you play any sports?",
                "How often do you exercise?",
                "Did you do sport at school?",
                "Is there a sport you would like to try?",
            ],
            "Describe a public event you attended.",
            ["what the event was", "where it was", "who you went with"],
            "why you remember this event",
            [
                "Why do people enjoy large public events?",
                "Should governments spend money on sports facilities?",
                "Do you think watching sport is as valuable as playing it?",
                "How might big events affect a local area?",
            ],
            "We've been talking about a public event, and I'd like to discuss with you one or two more general questions related to this.",
        ),
    ),
    _speaking(
        "s-weather-season",
        "Weather / a season you like",
        _pack(
            "Let's talk about the weather.",
            [
                "What is the weather like where you live?",
                "Do you prefer hot weather or cold weather?",
                "Does the weather affect your mood?",
                "What do you like to do on a rainy day?",
            ],
            "Describe a season you enjoy.",
            ["which season it is", "what the weather is like", "what you usually do then"],
            "why you enjoy this season",
            [
                "How does weather affect the way people live in your country?",
                "Do you think people worry more about climate than in the past?",
                "Should individuals or governments do more to protect the environment?",
                "How might daily life change if summers become much hotter?",
            ],
            "We've been talking about seasons and weather, and I'd like to discuss with you one or two more general questions related to this.",
        ),
    ),
]


def all_curated() -> list[dict[str, Any]]:
    return [*CURATED_WRITING, *CURATED_SPEAKING]
