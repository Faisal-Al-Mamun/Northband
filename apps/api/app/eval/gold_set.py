"""Gold essays for quote integrity and live band calibration."""

from __future__ import annotations

from typing import Any

# Human practice labels are approximate examiner-style bands, not official scores.
GOLD_WRITING: list[dict[str, Any]] = [
    {
        "id": "t2-mid-6",
        "module": "academic",
        "task": "task2",
        "prompt": "Some people believe unpaid community service should be compulsory in high school. To what extent do you agree or disagree?",
        "essay": (
            "Many students already have a heavy workload, so making community service compulsory may cause stress. "
            "However, I agree that some structured volunteering would help teenagers understand society. "
            "For example, helping in a local library teaches responsibility and communication. "
            "If schools keep the hours reasonable, the benefits can outweigh the pressure. "
            "In conclusion, a limited community programme should be part of high school, but it must not replace academic study."
        ),
        "human_overall": 6.0,
        "human_criteria": {
            "task_response": 6.0,
            "coherence": 6.0,
            "lexical": 6.0,
            "grammar": 6.0,
        },
        "must_quotes": ["making community service compulsory", "helping in a local library"],
    },
    {
        "id": "t2-low-5",
        "module": "academic",
        "task": "task2",
        "prompt": "Some people think universities should provide graduates with the knowledge and skills needed in the workplace. Others think the true function of a university is to give access to knowledge for its own sake. Discuss both views and give your opinion.",
        "essay": (
            "University is important for job. Some people say student need skill for work like computer and speaking. "
            "Other people say knowledge is for knowing things. I think both is needed because if you have only knowledge you cannot get job. "
            "Also if you only work skill you don't understand life. So university should teach job and knowledge."
        ),
        "human_overall": 5.0,
        "human_criteria": {
            "task_response": 5.0,
            "coherence": 5.0,
            "lexical": 5.0,
            "grammar": 4.5,
        },
        "must_quotes": ["University is important for job", "both is needed"],
    },
    {
        "id": "t2-high-7",
        "module": "academic",
        "task": "task2",
        "prompt": "In many countries, people are living longer. What problems does this cause and what measures could address them?",
        "essay": (
            "Rising life expectancy is a social achievement, yet it places pressure on pensions, hospitals, and family carers. "
            "When a larger share of the population is retired, governments must fund benefits from a smaller working base. "
            "Health systems also face more chronic illness, which is costly to treat. "
            "One response is to raise the retirement age gradually while expanding preventive care. "
            "Families can be supported with respite services so unpaid carers are not exhausted. "
            "In conclusion, longevity creates fiscal and medical strain, but staged pension reform and community care can reduce the burden."
        ),
        "human_overall": 7.0,
        "human_criteria": {
            "task_response": 7.0,
            "coherence": 7.0,
            "lexical": 7.0,
            "grammar": 7.0,
        },
        "must_quotes": ["Rising life expectancy is a social achievement", "staged pension reform"],
    },
    {
        "id": "gt-t1-letter",
        "module": "general",
        "task": "task1",
        "prompt": (
            "You stayed in a hotel and had problems with the room and service. Write a letter to the manager. "
            "In your letter: describe the problems, explain how they affected your stay, and say what you would like the manager to do."
        ),
        "essay": (
            "Dear Sir or Madam, I am writing about my stay at your hotel from 3 to 5 May. "
            "The air conditioning in room 214 did not work, and breakfast was served cold on both mornings. "
            "As a result I slept poorly and started each day tired before meetings. "
            "I would like a partial refund and an explanation of how you will prevent this. Yours faithfully, A. Rahman"
        ),
        "human_overall": 6.5,
        "human_criteria": {
            "task_response": 7.0,
            "coherence": 6.5,
            "lexical": 6.0,
            "grammar": 6.5,
        },
        "must_quotes": ["air conditioning in room 214", "partial refund"],
    },
    {
        "id": "ac-t1-short",
        "module": "academic",
        "task": "task1",
        "prompt": "The chart shows household ownership in England and Wales between 1918 and 2011. Summarise the information by selecting and reporting the main features.",
        "essay": (
            "The chart shows ownership and renting. Ownership went up and renting went down. "
            "In 1918 more people rented. In 2011 more people owned. That is the information in the chart."
        ),
        "human_overall": 5.0,
        "human_criteria": {
            "task_response": 5.0,
            "coherence": 5.0,
            "lexical": 5.0,
            "grammar": 5.0,
        },
        "must_quotes": ["Ownership went up and renting went down"],
    },
    {
        "id": "t2-thin-5-5",
        "module": "academic",
        "task": "task2",
        "prompt": "Some people believe that unpaid community service should be a compulsory part of high school programmes. To what extent do you agree or disagree?",
        "essay": (
            "I agree because community service is good for students. They can help people and learn new things. "
            "It is important for the future. Also it is good for society. Therefore I think schools should do this. "
            "However some students are busy so maybe it is difficult. In conclusion I agree with the idea."
        ),
        "human_overall": 5.5,
        "human_criteria": {
            "task_response": 5.5,
            "coherence": 5.5,
            "lexical": 5.0,
            "grammar": 5.5,
        },
        "must_quotes": ["community service is good for students"],
    },
    {
        "id": "t2-strong-8",
        "module": "academic",
        "task": "task2",
        "prompt": "Some people believe unpaid community service should be compulsory in high school. To what extent do you agree or disagree?",
        "essay": (
            "Compulsory volunteering sounds civic-minded, but mandating it risks turning service into a box-ticking exercise. "
            "When teenagers are assessed on hours rather than impact, they may resent the work and the recipients feel the difference. "
            "A more effective model is a well-designed optional programme with genuine choice: tutoring, conservation, or care-home visits. "
            "Schools can still set a modest expectation, such as one project in the senior years, without criminalising those who cannot participate because of paid work or family duties. "
            "In short, I disagree with a blanket requirement, yet I support structured opportunities that treat service as education rather than unpaid labour."
        ),
        "human_overall": 8.0,
        "human_criteria": {
            "task_response": 8.0,
            "coherence": 8.0,
            "lexical": 8.0,
            "grammar": 8.0,
        },
        "must_quotes": ["box-ticking exercise", "structured opportunities"],
    },
    {
        "id": "t2-grammar-heavy",
        "module": "academic",
        "task": "task2",
        "prompt": "Some people think the best way to reduce crime is to give longer prison sentences. Others believe there are better ways. Discuss both and give your opinion.",
        "essay": (
            "Longer prison is one way but it is not always work. If people stay more time in jail they maybe not do crime again. "
            "Other people say education and job is better because poor people do crime for money. "
            "I think government should use both. Prison for dangerous person and training for others. "
            "There is many reasons of crime so one solution is not enough. In conclusion mix of prison and education is best."
        ),
        "human_overall": 5.5,
        "human_criteria": {
            "task_response": 6.0,
            "coherence": 5.5,
            "lexical": 5.5,
            "grammar": 5.0,
        },
        "must_quotes": ["There is many reasons of crime", "mix of prison and education"],
    },
]


GOLD_SPEAKING: list[dict[str, Any]] = [
    {
        "id": "sp-p2-mid-6",
        "module": "academic",
        "task": "part2",
        "prompt": (
            "Describe a skill you would like to learn.\n"
            "You should say:\n"
            "- what the skill is\n"
            "- why you want to learn it\n"
            "- how you would learn it\n"
            "- and explain how this skill would help you"
        ),
        "transcript": (
            "I would like to learn pottery because it is relaxing after work. "
            "I would take a weekend class in my city and practise at home. "
            "This skill would help me slow down and also make gifts for friends."
        ),
        "human_overall": 6.0,
        "must_quotes": ["learn pottery because it is relaxing", "weekend class in my city"],
    },
    {
        "id": "sp-p1-thin-5",
        "module": "academic",
        "task": "part1",
        "prompt": "Let's talk about your hometown. What do you like about it?",
        "transcript": "My hometown is nice. I like the food. People is friendly. That is all I think.",
        "human_overall": 5.0,
        "must_quotes": ["People is friendly"],
    },
]


def all_gold() -> list[dict[str, Any]]:
    return [*GOLD_WRITING, *GOLD_SPEAKING]
