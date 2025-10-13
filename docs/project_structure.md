SOLOMIA/
├── .venv/
├── .gitignore
├── pyproject.toml
├── README.md
│
├── main.py                   # entry point
│
├── solomia/                  # src code
│   ├── __init__.py
│   ├── config.py             # tokens, settings
│   ├── core/                 # bot logic, handlers, services
│   │   ├── __init__.py
│   │   ├── handlers.py
│   │   ├── services.py
│   │   └── utils.py
│   └── models/               # pydantic-models or schemas
│       ├── __init__.py
│       └── user.py
│
└── tests/                    # unit-tests
    ├── __init__.py
    ├── test_handlers.py
    └── test_services.py