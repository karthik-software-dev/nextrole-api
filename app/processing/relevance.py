BACKEND_TITLE_KEYWORDS = [
    "backend",
    "back-end",
    "backend engineer",
    "backend developer",
    "server-side",
    "api engineer",
    "software engineer",
    "software developer",
    "platform engineer",
]

BACKEND_SKILL_KEYWORDS = [
    "python",
    "flask",
    "fastapi",
    "django",
    "rest api",
    "restful",
    "microservices",
    "distributed systems",
    "postgresql",
    "postgres",
    "mysql",
    "sql",
    "redis",
    "rabbitmq",
    "kafka",
    "celery",
    "aws",
    "azure",
    "gcp",
]

EXCLUDE_TITLE_KEYWORDS = [
    "intern",
    "internship",
    "frontend",
    "front end",
    "ui/ux",
    "android",
    "ios",
    "qa engineer",
    "qa automation",
    "test engineer",
    "testing engineer",
    "data analyst",
    "data scientist",
    "machine learning engineer",
    "ml engineer",
    "devops engineer",
    "site reliability engineer",
    "sre",
]


def calculate_relevance_score(job):
    title = (job.get("positionName") or "").lower()
    description = (job.get("description") or "").lower()

    score = 0

    # Strong backend title match
    for keyword in BACKEND_TITLE_KEYWORDS:
        if keyword in title:
            score += 5

    # Backend-related skills/concepts
    for keyword in BACKEND_SKILL_KEYWORDS:
        if keyword in description:
            score += 1

    # Exclude clearly unrelated roles
    for keyword in EXCLUDE_TITLE_KEYWORDS:
        if keyword in title:
            score -= 10

    return score


def filter_relevant_jobs(jobs, min_score=5):
    relevant_jobs = []

    for job in jobs:
        score = calculate_relevance_score(job)

        if score >= min_score:
            job["relevanceScore"] = score
            relevant_jobs.append(job)

    relevant_jobs.sort(
        key=lambda job: job["relevanceScore"],
        reverse=True,
    )

    return relevant_jobs