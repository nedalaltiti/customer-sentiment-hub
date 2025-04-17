# Customer Sentiment Hub

A modular and professional system for analyzing customer sentiment in debt resolution reviews using Google's Gemini models.

---

## 🔍 Features

- **Multi-label classification** – Identifies multiple topics within each review
- **Sentiment analysis** – Determines sentiment (`Positive`, `Negative`, `Neutral`) for each topic
- **Structured taxonomy** – Organizes feedback into categories and subcategories
- **Batch processing** – Efficiently processes large volumes of reviews
- **Modular architecture** – Well-organized code following software engineering best practices
- **Comprehensive validation** – Ensures outputs conform to the defined taxonomy
- **Configurable settings** – Easily customize behavior through environment variables

---

## ⚙️ Installation

### Using Poetry (recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/customer-sentiment-hub.git
cd customer-sentiment-hub

# Install dependencies
poetry install
```
# Project Structure
```
customer-sentiment-hub/
├── pyproject.toml
├── Makefile
├── .env.example
├── .pre-commit-config.yaml
├── README.md
├── src/
│   └── customer_sentiment_hub/
│       ├── __init__.py
│       ├── __main__.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── middleware.py
│       │   ├── models.py
│       │   └── routes.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   └── environment.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── taxonomy.py
│       │   ├── schema.py
│       │   └── validation.py
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── templates.py
│       │   └── formatters.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── llm_service.py
│       │   ├── gemini_service.py
│       │   └── processor.py
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── logging.py
│       │   ├── result.py
│       │   └── helpers.py
│       └── cli/
│           ├── __init__.py
│           ├── commands.py
│           └── app.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_taxonomy.py
│   │   ├── test_schema.py
│   │   └── test_validation.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_analyzer.py
│   └── fixtures/
│       ├── __init__.py
│       ├── reviews.json
│       └── responses.json
└── docs/
    ├── index.md
    ├── user_guide.md
    ├── api.md
    └── development.md
```
