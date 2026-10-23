# CLAUDE.md - Python Domain-Driven Design & Clean Code Standards

## 1. Architektur-Prinzipien (Clean Architecture / Hexagonal)
Dieses Projekt folgt streng den Prinzipien des Domain-Driven Designs (DDD). Die Abhängigkeiten zeigen *nur* nach innen:

1. **Domain Layer (Core):**
   - Enthält Entities, Value Objects, Domain Services und Repository-Interfaces (`abc.ABC`).
   - **Absolute Regel:** Null Abhängigkeiten zu Frameworks (kein FastAPI, Django, SQLAlchemy) oder externen Bibliotheken (außer Standard-Bibliothek).
2. **Application Layer:**
   - Enthält Use Cases / Command- und Query-Handler.
   - Steuert Transaktionen und mappt Domain-Modelle auf DTOs. Kennt die Domain, aber keine UI oder Infrastruktur-Details.
3. **Infrastructure Layer:**
   - Enthält DB-Implementierungen (SQLAlchemy Models, Alembic), externe APIs und konkrete Repository-Klassen.
4. **Presentation Layer:**
   - FastAPI-Router, CLI-Befehle oder Entrypoints. Übersetzt Requests in Use-Case-Aufrufe.

---

## 2. Datenmodelle & Value Objects
- **Domain-Kern:** Nutze standardmäßig `dataclasses.dataclass(frozen=True)` für Value Objects und Entities im Domain-Layer (Zero Dependencies). Validierung erfolgt explizit in `__post_init__`.
- **Ausnahme für Pydantic:** Pydantic-Modelle (`frozen=True`) sind im Domain-Layer *nur* erlaubt, wenn komplexe Validierungsregeln (z. B. komplexe Regex, verschachtelte Strukturen) den Boilerplate-Aufwand in `__post_init__` sprengen würden.
- **Application & Presentation:** In diesen Schichten ist Pydantic der Standard für DTOs, API-Requests und Konfigurationen.

---

## 3. Code-Qualität & Clean Code (Lesbarkeit hat Priorität)
- **Single Responsibility:** Jede Funktion, Klasse und jedes Modul hat exakt eine Verantwortung. 
- **Maximale Länge:** Eine Funktion darf maximal 20 Zeilen lang sein; Docstrings zählen dabei nicht mit. Überschreitet eine Datei 250 Zeilen (ohne Kommentare), muss sie modular aufgeteilt werden.
- **Guard Clauses statt If/Else-Wüsten:** Verwende konsequent Early Returns, um Fehlerfälle oder Edge Cases am Anfang einer Funktion abzufangen. Vermeide tiefe Einrückungen und komplexe logische Verknüpfungen in `if`-Bedingungen.
- **Vollständige Typisierung:** Jede Funktion und Methode MUSS vollständig typisiert sein (`mypy`-kompatibel). Nutze `from __future__ import annotations`.
- **Namen sind Dokumentation:** Verwende präzise, aussagekräftige Namen (`user_repository` statt `repo`). Keine einletterigen Variablen außer in kurzen Schleifen.
- **Keine Cleverness:** Schreibe expliziten, lesbaren Code. Keine versteckten Seiteneffekte oder unnötige Metaprogrammierung.

---

## 4. Verzeichnisstruktur (Beispiel)
src/
├── domain/               # Reine Geschäftslogik (Entities, VOs, Interfaces)
│   ├── model/
│   ├── services/
│   └── repositories.py   # Abstrakte Interfaces (ABC)
├── application/          # Use Cases / Application Services
│   ├── commands/
│   └── queries/
├── infrastructure/       # Datenbank, Externe APIs
│   ├── persistence/      # SQLAlchemy, Alembic
│   └── web/              # FastAPI Router
└── presentation/         # Entrypoints (CLI, Web-App)

---

## 5. Regeln für Claude bei der Code-Generierung
- **Keine Framework-Logik in der Domain:** Achte strikt darauf, dass Domain-Objekte niemals SQLAlchemy-Modelle oder FastAPI-Abhängigkeiten importieren.
- **Repository Pattern:** Use Cases greifen niemals direkt auf Datenbanken zu, sondern nutzen ausschließlich die abstrakten Repository-Interfaces der Domain.
- **Inkrementelles Arbeiten:** Bei größeren Features: Erstelle zuerst die Domain-Logik, frage nach Feedback, erst danach Use Cases und Infrastruktur.
