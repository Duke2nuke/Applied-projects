"""Sample data for the resume-JD matcher.

Everything here is SYNTHETIC and fictional: a made-up candidate profile
and made-up job descriptions. Nothing here is a real person's resume or
a real company's posting. Swap SAMPLE_RESUME for your own resume text
and JOBS for real postings to use this for a real search.
"""

SAMPLE_RESUME = """
Sample Candidate — B.Tech student, Computer Science (AI/ML).
Skills: Python, SQL, pandas, NumPy, scikit-learn, Git, statistics.
Projects: built a text classifier with TF-IDF and logistic regression;
built a small dashboard that plots model metrics with Matplotlib.
Coursework: machine learning, data structures, probability.
Looking for: a machine learning or data science internship, remote.
"""

JOBS = [
    {
        "id": "ml-intern",
        "title": "Machine Learning Intern",
        "company": "Fictional ML Labs",
        "description": """
            Machine learning internship. You will build and evaluate
            classification models in Python using scikit-learn and pandas,
            clean data with SQL, and report results with statistics and
            data visualization. Experience with machine learning coursework
            and Git is expected. Knowledge of deep learning is a plus.
        """,
    },
    {
        "id": "ds-intern",
        "title": "Data Science Intern",
        "company": "Fictional Analytics Co",
        "description": """
            Data science internship. Analyse datasets in Python with pandas
            and NumPy, write SQL queries, apply statistics, and present
            findings with data visualization and Matplotlib. Familiarity
            with machine learning is helpful.
        """,
    },
    {
        "id": "backend-intern",
        "title": "Backend Developer Intern",
        "company": "Fictional Cloud Co",
        "description": """
            Backend internship. Build REST APIs with Flask and FastAPI,
            work with PostgreSQL and MongoDB, deploy services with Docker
            and AWS, and manage Linux servers. Python is useful but the
            focus is APIs, databases, and cloud infrastructure.
        """,
    },
    {
        "id": "frontend-intern",
        "title": "Frontend Developer Intern",
        "company": "Fictional Web Studio",
        "description": """
            Frontend internship. Build user interfaces with React,
            JavaScript, TypeScript, HTML and CSS. Experience with
            Node.js and responsive design is expected. No machine
            learning work in this role.
        """,
    },
    {
        "id": "devops-intern",
        "title": "DevOps Intern",
        "company": "Fictional Infra Co",
        "description": """
            DevOps internship. Manage CI pipelines, Docker containers,
            Kubernetes clusters, and AWS infrastructure. Linux and Git
            required; scripting in Python is a bonus.
        """,
    },
    {
        "id": "cv-intern",
        "title": "Computer Vision Research Intern",
        "company": "Fictional Vision Lab",
        "description": """
            Research internship in computer vision. Requires deep learning
            with PyTorch or TensorFlow, image processing, and strong
            mathematics. Prior computer vision project work is essential.
        """,
    },
]
