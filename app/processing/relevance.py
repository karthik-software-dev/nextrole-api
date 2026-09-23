import re
from models.job import Job

# ----------------------------------------------------------------------
# 1. HARD TITLE EXCLUSIONS
# Any occurrence of these in the job title instantly disqualifies the role.
# ----------------------------------------------------------------------
HARD_EXCLUDE_TITLE_KEYWORDS = [
    # Senior Leadership / Executive / Overly Senior (Beyond 1-5 Yrs experience target)
    "director",
    "vp",
    "vice president",
    "head of",
    "engineering manager",
    "general manager",
    "manager",
    "chief",
    "principal",
    "staff",
    "lead",
    "architect",
    "distinguished",
    # Academic & Pure Research (Not Software/Backend Engineering)
    "phd",
    "research scientist",
    "ai researcher",
    "ml researcher",
    "research fellow",
    # QA & Testing
    "qa",
    "quality engineer",
    "test",
    "tester",
    "testing",
    "sdet",
    "verification engineer",
    "verification",
    "automation engineer",
    "selenium",
    # Sales, Pre-sales, GTM & Training
    "solution engineer",
    "sales engineer",
    "trainer",
    "learning specialist",
    "gtm engineer",
    # Enterprise ERP & Non-Target Consulting
    "oracle cloud",
    "oracle stack",
    "sap",
    "salesforce",
    # Analytics, Non-SWE & Support
    "analyst",
    "data scientist",
    "support engineer",
    "technical support",
    "network engineer",
    # Pure Machine Learning / Data Science
    "ml engineer",
    "machine learning engineer",
    # Early Career / Trainee
    "intern",
    "internship",
    "trainee",
    "graduate trainee",
]

# ----------------------------------------------------------------------
# 2. TITLE ALIGNMENT TIERS
# ----------------------------------------------------------------------
PRIMARY_TITLE_KEYWORDS = [
    "python backend engineer",
    "python backend developer",
    "python backend",
    "backend engineer",
    "backend developer",
    "back end engineer",
    "back-end engineer",
    "back end developer",
    "back-end developer",
    "api engineer",
    "server-side engineer",
    "server-side",
    "backend platform engineer",
    "backend-focused full stack",
    "backend focused full stack",
    "backend-focused",
    "software engineer, backend",
    "software engineer - backend",
    "software engineer (backend)",
    "sde backend",
    "sde - backend",
    "sde ii - backend",
    "backend leaning",
]

STRONG_TITLE_KEYWORDS = [
    "python engineer",
    "python developer",
    "backend",
    "back-end",
    "distributed systems engineer",
    "distributed systems",
    "ai engineer (backend)",
    "python ai engineer",
]

SECONDARY_TITLE_KEYWORDS = [
    "platform engineer",
    "full stack engineer",
    "fullstack engineer",
    "full-stack engineer",
    "full stack developer",
    "fullstack developer",
    "full-stack developer",
    "full stack",
    "fullstack",
    "full-stack",
]

GENERIC_TITLE_KEYWORDS = [
    "software engineer",
    "software developer",
    "sde",
    "sde 1", "sde 2", "sde 3",
    "sde i", "sde ii", "sde iii",
    "sde-1", "sde-2", "sde-3",
    "sde1", "sde2", "sde3",
    "full stack engineer",
    "fullstack engineer",
    "full-stack engineer",
    "full stack developer",
    "fullstack developer",
    "full-stack developer",
    "full stack",
    "fullstack",
    "full-stack",
    "platform engineer",
    "application development engineer",
]

# Concrete Technical Backend Skills for Generic Evidence Verification
# Excludes broad/boilerplate words like 'system design', generic 'api', generic 'database'
CONCRETE_BACKEND_SIGNALS = [
    # Frameworks
    "fastapi", "flask", "django", "django rest framework", "drf",
    # Databases & Storage
    "postgresql", "postgres", "mysql", "sql", "sqlalchemy", "redis", "mongodb", "orm", "alembic",
    # Architecture, APIs & Queues
    "rest api", "rest apis", "restful api", "restful apis", "restful",
    "microservices", "distributed systems", "rabbitmq", "celery", "kafka",
    "grpc", "asyncio", "websocket", "websockets", "event-driven", "event driven",
]

# ----------------------------------------------------------------------
# 3. SKILL TAXONOMY & CANONICAL CONCEPT MAPPING
# Prevents synonym double-counting (e.g., Postgres + PostgreSQL, REST API + RESTful)
# ----------------------------------------------------------------------
SKILL_TAXONOMY: dict[str, dict[str, tuple[str, str]]] = {
    "BACKEND": {
        "python": ("python", "Python"),
        "fastapi": ("fastapi", "FastAPI"),
        "flask": ("flask", "Flask"),
        "django": ("django", "Django"),
        "django rest framework": ("drf", "DRF"),
        "drf": ("drf", "DRF"),
        "rest api": ("rest_api", "REST API"),
        "rest apis": ("rest_api", "REST API"),
        "restful api": ("rest_api", "REST API"),
        "restful apis": ("rest_api", "REST API"),
        "restful": ("rest_api", "REST API"),
        "api development": ("rest_api", "REST API"),
        "sqlalchemy": ("sqlalchemy", "SQLAlchemy"),
        "alembic": ("alembic", "Alembic"),
        "orm": ("orm", "ORM"),
        "pydantic": ("pydantic", "Pydantic"),
        "grpc": ("grpc", "gRPC"),
        "websocket": ("websocket", "WebSocket"),
        "websockets": ("websocket", "WebSocket"),
        "asyncio": ("asyncio", "Asyncio"),
        "jwt": ("jwt", "JWT"),
        "oauth": ("oauth", "OAuth"),
        "oauth2": ("oauth", "OAuth2"),
        "rbac": ("rbac", "RBAC"),
        "authentication": ("auth", "Authentication"),
        "authorization": ("auth", "Authorization"),
        "session auth": ("auth", "Session Auth"),
        "bcrypt": ("bcrypt", "Bcrypt"),
        "api security": ("api_security", "API Security"),
    },
    "ARCHITECTURE": {
        "microservices": ("microservices", "Microservices"),
        "distributed systems": ("distributed_systems", "Distributed Systems"),
        "system design": ("system_design", "System Design"),
        "scalability": ("scalability", "Scalability"),
        "event-driven architecture": ("event_driven", "Event-Driven"),
        "event-driven": ("event_driven", "Event-Driven"),
        "event driven": ("event_driven", "Event-Driven"),
        "background tasks": ("background_tasks", "Background Tasks"),
        "background jobs": ("background_tasks", "Background Tasks"),
        "task queue": ("task_queue", "Task Queue"),
        "message queue": ("message_queue", "Message Queue"),
        "caching": ("caching", "Caching"),
        "load balancing": ("load_balancing", "Load Balancing"),
        "rate limiting": ("rate_limiting", "Rate Limiting"),
        "api gateway": ("api_gateway", "API Gateway"),
        "concurrency": ("concurrency", "Concurrency"),
        "event loop": ("event_loop", "Event Loop"),
    },
    "DATABASE": {
        "postgresql": ("postgresql", "PostgreSQL"),
        "postgres": ("postgresql", "PostgreSQL"),
        "mysql": ("mysql", "MySQL"),
        "sqlite": ("sqlite", "SQLite"),
        "sql": ("sql", "SQL"),
        "mongodb": ("mongodb", "MongoDB"),
        "dynamodb": ("dynamodb", "DynamoDB"),
        "redis": ("redis", "Redis"),
        "memcached": ("memcached", "Memcached"),
        "database design": ("db_design", "DB Design"),
        "db design": ("db_design", "DB Design"),
        "query optimization": ("query_optimization", "Query Optimization"),
        "indexing": ("db_indexing", "DB Indexing"),
        "db indexing": ("db_indexing", "DB Indexing"),
        "database indexing": ("db_indexing", "DB Indexing"),
        "acid": ("acid_tx", "ACID"),
        "transactions": ("acid_tx", "ACID Transactions"),
        "acid transactions": ("acid_tx", "ACID Transactions"),
        "partitioning": ("partitioning", "Partitioning"),
        "connection pooling": ("connection_pooling", "Connection Pooling"),
        "row level security": ("row_level_security", "Row-Level Security"),
        "row-level security": ("row_level_security", "Row-Level Security"),
    },
    "INFRASTRUCTURE": {
        "rabbitmq": ("rabbitmq", "RabbitMQ"),
        "celery": ("celery", "Celery"),
        "kafka": ("kafka", "Kafka"),
        "docker": ("docker", "Docker"),
        "dockerfile": ("docker", "Dockerfile"),
        "docker compose": ("docker_compose", "Docker Compose"),
        "docker-compose": ("docker_compose", "Docker Compose"),
        "kubernetes": ("kubernetes", "Kubernetes"),
        "aws": ("aws", "AWS"),
        "ec2": ("aws_ec2", "EC2"),
        "s3": ("aws_s3", "S3"),
        "rds": ("aws_rds", "RDS"),
        "gcp": ("gcp", "GCP"),
        "azure": ("azure", "Azure"),
        "nginx": ("nginx", "Nginx"),
        "reverse proxy": ("reverse_proxy", "Reverse Proxy"),
        "gunicorn": ("gunicorn", "Gunicorn"),
        "linux": ("linux", "Linux"),
        "ci/cd": ("cicd", "CI/CD"),
        "gitlab ci": ("gitlab_ci", "GitLab CI"),
        "github actions": ("github_actions", "GitHub Actions"),
        "git": ("git", "Git"),
        "github": ("github", "GitHub"),
        "gitlab": ("gitlab", "GitLab"),
    },
    "FULL_STACK": {
        "react": ("react", "React"),
        "react.js": ("react", "React.js"),
        "javascript": ("javascript", "JavaScript"),
        "typescript": ("typescript", "TypeScript"),
        "jsx": ("jsx", "JSX"),
        "next.js": ("nextjs", "Next.js"),
        "nextjs": ("nextjs", "Next.js"),
        "tailwind": ("tailwind", "Tailwind CSS"),
        "tailwind css": ("tailwind", "Tailwind CSS"),
        "css3": ("css3", "CSS3"),
        "responsive design": ("responsive_design", "Responsive Design"),
        "shadcn": ("shadcn", "Shadcn/UI"),
        "shadcn/ui": ("shadcn", "Shadcn/UI"),
        "redux": ("redux", "Redux"),
        "redux toolkit": ("redux", "Redux Toolkit"),
        "zustand": ("zustand", "Zustand"),
        "react query": ("react_query", "React Query"),
        "tanstack query": ("react_query", "TanStack Query"),
        "react router": ("react_router", "React Router"),
        "axios": ("axios", "Axios"),
        "single page application": ("spa", "SPA"),
        "spa": ("spa", "SPA"),
    },
    "AI_BACKEND": {
        "llm": ("llm", "LLM"),
        "llms": ("llm", "LLM"),
        "large language model": ("llm", "LLM"),
        "large language models": ("llm", "LLM"),
        "rag": ("rag", "RAG"),
        "genai": ("genai", "GenAI"),
        "generative ai": ("genai", "Generative AI"),
        "langchain": ("langchain", "LangChain"),
        "langgraph": ("langgraph", "LangGraph"),
        "llamaindex": ("llamaindex", "LlamaIndex"),
        "crewai": ("crewai", "CrewAI"),
        "ai agents": ("ai_agents", "AI Agents"),
        "ai agent": ("ai_agents", "AI Agents"),
        "embeddings": ("embeddings", "Embeddings"),
        "vector embeddings": ("embeddings", "Embeddings"),
        "vector database": ("vector_db", "Vector DB"),
        "pgvector": ("pgvector", "pgvector"),
        "pinecone": ("pinecone", "Pinecone"),
        "qdrant": ("qdrant", "Qdrant"),
        "milvus": ("milvus", "Milvus"),
        "chromadb": ("chromadb", "ChromaDB"),
        "faiss": ("faiss", "FAISS"),
        "semantic search": ("semantic_search", "Semantic Search"),
        "hybrid search": ("hybrid_search", "Hybrid Search"),
        "reranking": ("reranking", "Reranking"),
        "prompt engineering": ("prompt_engineering", "Prompt Engineering"),
        "function calling": ("function_calling", "Function Calling"),
        "tool calling": ("tool_calling", "Tool Calling"),
        "mcp": ("mcp", "MCP"),
        "openai": ("openai", "OpenAI"),
        "anthropic": ("anthropic", "Anthropic"),
        "gemini": ("gemini", "Gemini"),
        "ollama": ("ollama", "Ollama"),
        "huggingface": ("huggingface", "HuggingFace"),
    },
}

CATEGORY_CONFIG: dict[str, dict[str, float]] = {
    "BACKEND": {"point_per_match": 3.0, "cap": 12.0},
    "ARCHITECTURE": {"point_per_match": 2.5, "cap": 8.0},
    "DATABASE": {"point_per_match": 2.0, "cap": 8.0},
    "AI_BACKEND": {"point_per_match": 2.0, "cap": 6.0},
    "FULL_STACK": {"point_per_match": 1.5, "cap": 4.0},
    "INFRASTRUCTURE": {"point_per_match": 1.0, "cap": 4.0},
}


def _has_keyword(keyword: str, text: str) -> bool:
    """Checks for keyword presence using word boundaries to prevent substring collisions."""
    pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
    return bool(re.search(pattern, text, re.IGNORECASE))


def calculate_relevance_score(job: Job) -> tuple[float, list[str]]:
    """Evaluates a Job against candidate preferences with V6 precision.

    Returns:
        tuple[float, list[str]]: (calculated score, list of matched skill highlights)
    """
    title = (job.title or "").lower()
    description = (job.description or "").lower()
    full_text = f"{title} {description}"
    matched_skills: list[str] = []

    # 1. Hard Disqualification Filter
    for exclude_word in HARD_EXCLUDE_TITLE_KEYWORDS:
        if _has_keyword(exclude_word, title):
            return -100.0, []

    # 2. Strict Seniority & Experience Disqualifications (> 5 yrs min is disqualified)
    if job.experience_min is not None and job.experience_min > 5:
        return -100.0, []

    high_exp_pattern = r"\b(?:minimum|at\s+least|min)?\s*([6-9]|[1-2][0-9])\+\s*(?:years?|yrs?)"
    if re.search(high_exp_pattern, full_text, re.IGNORECASE):
        return -100.0, []

    # 3. Must-Have Baseline
    has_python = _has_keyword("python", title) or _has_keyword("python", description)
    has_backend = any(_has_keyword(k, full_text) for k in [
        "backend", "back-end", "api", "fastapi", "flask", "django", "microservices", "distributed systems"
    ])
    if not (has_python or has_backend):
        return 0.0, []

    # 3b. Generic & Full Stack Role Evidence Check
    is_primary_or_strong = any(_has_keyword(k, title) for k in PRIMARY_TITLE_KEYWORDS + STRONG_TITLE_KEYWORDS)
    is_generic_role = (not is_primary_or_strong) and any(_has_keyword(k, title) for k in GENERIC_TITLE_KEYWORDS)

    if is_generic_role:
        # Require Python AND at least 1 concrete backend skill (Framework, DB/ORM, or API/Distributed Architecture)
        matched_backend_signals = [k for k in CONCRETE_BACKEND_SIGNALS if _has_keyword(k, description)]
        if not has_python or len(matched_backend_signals) < 1:
            return 0.0, []

    score = 0.0

    # 4. Title Alignment Scoring
    if any(_has_keyword(k, title) for k in PRIMARY_TITLE_KEYWORDS):
        score += 10.0
    elif any(_has_keyword(k, title) for k in STRONG_TITLE_KEYWORDS):
        score += 7.0
    elif any(_has_keyword(k, title) for k in SECONDARY_TITLE_KEYWORDS):
        score += 4.0
    elif is_generic_role:
        score += 1.0

    # 5. Canonical Description Skill Matching with Category Caps
    seen_canonical_concepts: set[str] = set()
    total_skill_points = 0.0

    for cat_name, cat_skills in SKILL_TAXONOMY.items():
        cat_points = 0.0
        cfg = CATEGORY_CONFIG[cat_name]
        for kw, (concept_key, display_name) in cat_skills.items():
            if concept_key not in seen_canonical_concepts and _has_keyword(kw, description):
                seen_canonical_concepts.add(concept_key)
                cat_points += cfg["point_per_match"]
                matched_skills.append(display_name)
        total_skill_points += min(cat_points, cfg["cap"])

    # Global description cap prevents buzzword inflation
    score += min(total_skill_points, 18.0)

    # 6. Multi-Stack Synergy Bonuses
    has_fe = any(k in seen_canonical_concepts for k in ["react", "javascript", "typescript", "nextjs"])
    has_ai = any(k in seen_canonical_concepts for k in ["llm", "rag", "langchain", "vector_db", "ai_agents", "mcp"])
    if has_fe and (has_python or has_backend):
        score += 2.0
        matched_skills.append("Full-Stack Synergy")
    if has_ai and has_python:
        score += 2.0
        matched_skills.append("AI-Backend Synergy")

    # 7. Experience Curve Scoring & Penalties (Target: 1-5 Years)
    if job.experience_min is not None:
        if job.experience_min <= 3 and (job.experience_max is not None and job.experience_max <= 3):
            score += 3.0
            matched_skills.append("Sweet-Spot Exp (1-3 Yrs)")
        elif job.experience_min <= 3 and (job.experience_max is None or job.experience_max <= 5):
            score += 2.0
            matched_skills.append("Sweet-Spot Exp (1-5 Yrs)")
        elif job.experience_min == 4 and (job.experience_max is not None and job.experience_max <= 5):
            pass  # Neutral: acceptable 4-5 yrs
        elif job.experience_min >= 4 and job.experience_max is None:
            # 4+ Yrs without upper bound leans senior
            score -= 3.0
            matched_skills.append("Senior Exp (4+ Yrs)")
        elif job.experience_max is not None and job.experience_max >= 6:
            # Over-wide senior range (e.g. 2-7, 3-6, 4-9 yrs)
            score -= 4.0
            matched_skills.append("Senior Range Penalty")
        elif job.experience_min >= 5:
            score -= 6.0
            matched_skills.append("High Exp Penalty")

    # 8. Senior Title Negative Penalty (Roles titled 'Senior' or 'Sr.')
    is_senior_title = bool(re.search(r"\b(?:senior|sr\.?)\b", title, re.IGNORECASE))
    if is_senior_title:
        if job.experience_min is not None and job.experience_min >= 5:
            return -100.0, []  # Disqualify senior title with 5+ yrs
        score -= 5.0
        matched_skills.append("Senior Role Penalty")

    # SDE-1 / SDE-2 Target Role
    sde_keywords = [
        "sde 1", "sde i", "sde 2", "sde ii", "sde-1", "sde-2", "sde1", "sde2",
        "software engineer 1", "software engineer i",
        "software engineer 2", "software engineer ii", "associate",
    ]
    if any(_has_keyword(k, title) for k in sde_keywords):
        score += 2.0
        matched_skills.append("SDE-1/2 Target Role")

    return score, matched_skills


def filter_relevant_jobs(jobs: list[Job], min_score: float = 8.0) -> list[Job]:
    """Filters, scores, and ranks normalized Job objects based on relevance score."""
    relevant_jobs: list[Job] = []

    for job in jobs:
        score, matched = calculate_relevance_score(job)
        job.relevance_score = score
        job.matched_skills = matched

        if score >= min_score:
            relevant_jobs.append(job)

    relevant_jobs.sort(
        key=lambda j: j.relevance_score,
        reverse=True,
    )

    return relevant_jobs