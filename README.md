# Streamlit-Karteikarten-Trainer

## Starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Ordnerstruktur

```text
streamlit_karteikarten/
├─ app.py
├─ requirements.txt
├─ topics/
│  ├─ physikalische_chemie.json
│  └─ organische_chemie.json
└─ media/
   └─ diffusion_beispiel.png
```

Die App erkennt automatisch jede `.json`-Datei im Ordner `topics`.

## Format einer Themen-Datei

```json
{
  "title": "Mein Thema",
  "description": "Kurze Beschreibung",
  "cards": [
    {
      "heading": "Überschrift der Karte",
      "question": "Einfache Textfrage",
      "answer": "Einfache Textantwort"
    }
  ]
}
```

Frage und Antwort dürfen auch aus mehreren Blöcken bestehen:

```json
{
  "heading": "Gemischter Inhalt",
  "question": [
    {
      "type": "text",
      "content": "Wie lautet die Gleichung?"
    },
    {
      "type": "latex",
      "content": "J=-D\\frac{\\mathrm{d}c}{\\mathrm{d}z}"
    },
    {
      "type": "image",
      "content": "../media/mein_bild.png",
      "caption": "Optionale Bildunterschrift"
    }
  ],
  "answer": [
    {
      "type": "markdown",
      "content": "Hier darf **Markdown** stehen."
    }
  ]
}
```

Unterstützte Inhaltstypen:

- `text`
- `markdown`
- `latex`
- `image`

Bildpfade werden relativ zur jeweiligen Themen-Datei interpretiert.
