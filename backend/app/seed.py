from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .models import MentorshipRequest, Session as MentorshipSession, Skill, User, UserSkill
from .security import hash_password

SKILLS = [
    ("Product strategy", "Product"),
    ("Career transitions", "Career"),
    ("Staff engineering", "Engineering"),
    ("Engineering management", "Engineering"),
    ("Design systems", "Design"),
    ("Data science", "Data"),
    ("Founder sales", "Business"),
    ("Research to industry", "Career"),
    ("Brand & storytelling", "Design"),
    ("Interview prep", "Career"),
    ("Leadership presence", "Leadership"),
    ("System design", "Engineering"),
    ("IC to manager", "Leadership"),
    ("Fundraising", "Business"),
    ("UX research", "Design"),
]

MENTORS = [
    {
        "email": "amara@mentorwow.app",
        "name": "Amara Okonkwo",
        "headline": "Product lead who has shipped three 0→1 products",
        "bio": "I help mid-career PMs stop treating roadmap as a to-do list. We work on judgment, stakeholder theater, and the messy art of saying no without burning the room down.",
        "location": "Lagos / London",
        "availability": "Tue & Thu evenings",
        "years_experience": 12,
        "accent": "#C24A2A",
        "skills": ["Product strategy", "Leadership presence", "Interview prep"],
    },
    {
        "email": "julian@mentorwow.app",
        "name": "Julian Park",
        "headline": "Staff engineer, distributed systems, patient explainer",
        "bio": "Fifteen years of making services fail more gracefully. Best for engineers aiming at staff: scope, influence without authority, and writing design docs people actually read.",
        "location": "Seoul / Remote",
        "availability": "Weekend mornings",
        "years_experience": 15,
        "accent": "#3F6B5C",
        "skills": ["Staff engineering", "System design", "Engineering management"],
    },
    {
        "email": "priya@mentorwow.app",
        "name": "Priya Mehta",
        "headline": "From consulting to data science, without the myth of a clean leap",
        "bio": "I made the jump with a toddler, a mortgage, and a portfolio that was honestly mid. We build a realistic plan: projects, narrative, and the interviews that actually hire.",
        "location": "Austin",
        "availability": "Weekday lunches",
        "years_experience": 9,
        "accent": "#8B5A2B",
        "skills": ["Data science", "Career transitions", "Interview prep"],
    },
    {
        "email": "diego@mentorwow.app",
        "name": "Diego Alvarez",
        "headline": "Founder who learned to sell before the deck was pretty",
        "bio": "Two companies, one acquisition, many awkward cold calls. I mentor first-time founders on founder-led sales, pricing courage, and not hiding behind product.",
        "location": "Mexico City",
        "availability": "Mon / Wed afternoons",
        "years_experience": 11,
        "accent": "#9A351C",
        "skills": ["Founder sales", "Fundraising", "Leadership presence"],
    },
    {
        "email": "naomi@mentorwow.app",
        "name": "Naomi Chen",
        "headline": "Design systems, craft, and the IC-to-manager hinge",
        "bio": "I ran a design system used by 80 product teams. Mentorship is for designers who want sharper critique, systems thinking, and a honest read on whether management is actually the move.",
        "location": "Toronto",
        "availability": "Friday mornings",
        "years_experience": 10,
        "accent": "#2F4F6B",
        "skills": ["Design systems", "IC to manager", "UX research"],
    },
    {
        "email": "samira@mentorwow.app",
        "name": "Samira Hassan",
        "headline": "PhD to industry without shrinking your curiosity",
        "bio": "I left a lab, kept the rigor, and learned to talk about impact in a language hiring managers hear. For researchers translating a thesis into a job they will not resent.",
        "location": "Berlin",
        "availability": "Evenings, CET",
        "years_experience": 8,
        "accent": "#6B3F5C",
        "skills": ["Research to industry", "Career transitions", "Interview prep"],
    },
    {
        "email": "theo@mentorwow.app",
        "name": "Theo Brooks",
        "headline": "Creative director for brands that need a point of view",
        "bio": "I help makers and marketers find a voice that is not a moodboard. Story, craft, and how to present work so it feels inevitable instead of decorative.",
        "location": "Brooklyn",
        "availability": "Wed evenings",
        "years_experience": 14,
        "accent": "#C9A227",
        "skills": ["Brand & storytelling", "Leadership presence", "UX research"],
    },
    {
        "email": "malik@mentorwow.app",
        "name": "Malik Johnson",
        "headline": "Engineering manager who still writes the hard tickets",
        "bio": "I coach new managers through 1:1s, leveling, and the first performance conversation that keeps you up at night. Also good for ICs deciding if they even want the chair.",
        "location": "Chicago",
        "availability": "Thu afternoons",
        "years_experience": 13,
        "accent": "#1F4B3A",
        "skills": ["Engineering management", "IC to manager", "Leadership presence"],
    },
]

MENTEE = {
    "email": "mentee@mentorwow.app",
    "name": "Riley Shah",
    "headline": "PM looking for sharper product judgment",
    "bio": "Four years in B2B SaaS. I want a mentor who will tell me when my roadmap is a wish list.",
    "location": "Denver",
    "availability": "Flexible evenings",
    "years_experience": 4,
    "accent": "#C24A2A",
    "skills": ["Product strategy", "Interview prep"],
}


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return

    skills_by_name: dict[str, Skill] = {}
    for name, category in SKILLS:
        skill = Skill(name=name, category=category)
        db.add(skill)
        db.flush()
        skills_by_name[name] = skill

    password = hash_password("mentorwow")
    mentors: list[User] = []
    for data in MENTORS:
        user = User(
            email=data["email"],
            hashed_password=password,
            name=data["name"],
            role="mentor",
            headline=data["headline"],
            bio=data["bio"],
            location=data["location"],
            availability=data["availability"],
            years_experience=data["years_experience"],
            accent=data["accent"],
        )
        db.add(user)
        db.flush()
        for skill_name in data["skills"]:
            db.add(UserSkill(user_id=user.id, skill_id=skills_by_name[skill_name].id, kind="teaching"))
        mentors.append(user)

    mentee = User(
        email=MENTEE["email"],
        hashed_password=password,
        name=MENTEE["name"],
        role="mentee",
        headline=MENTEE["headline"],
        bio=MENTEE["bio"],
        location=MENTEE["location"],
        availability=MENTEE["availability"],
        years_experience=MENTEE["years_experience"],
        accent=MENTEE["accent"],
    )
    db.add(mentee)
    db.flush()
    for skill_name in MENTEE["skills"]:
        db.add(UserSkill(user_id=mentee.id, skill_id=skills_by_name[skill_name].id, kind="learning"))

    now = datetime.now(timezone.utc)
    accepted = MentorshipRequest(
        mentee_id=mentee.id,
        mentor_id=mentors[0].id,
        goal="Get ready for a principal PM interview loop",
        message="Amara, I have a loop in six weeks and my product sense stories still sound like feature recaps. I would love a monthly critique plus a mock.",
        status="accepted",
        created_at=now - timedelta(days=12),
    )
    pending = MentorshipRequest(
        mentee_id=mentee.id,
        mentor_id=mentors[1].id,
        goal="Level up system design for staff conversations",
        message="Julian, I keep freezing on tradeoff questions. Looking for a mentor who will make me draw the diagram out loud.",
        status="pending",
        created_at=now - timedelta(days=2),
    )
    db.add_all([accepted, pending])
    db.flush()

    db.add(
        MentorshipSession(
            request_id=accepted.id,
            mentee_id=mentee.id,
            mentor_id=mentors[0].id,
            title="Product sense mock: marketplace matching",
            scheduled_at=now + timedelta(days=4, hours=3),
            duration_minutes=45,
            status="scheduled",
        )
    )
    db.add(
        MentorshipSession(
            request_id=accepted.id,
            mentee_id=mentee.id,
            mentor_id=mentors[0].id,
            title="Roadmap teardown",
            scheduled_at=now - timedelta(days=6),
            duration_minutes=50,
            status="completed",
            notes="Riley's Q3 roadmap had eight 'bets' and no killing criteria. Homework: rewrite as three bets with explicit anti-goals.",
        )
    )
    db.commit()
