# Kinshasa Gift Hub × KinCards

Application web moderne pour vendre des cartes cadeaux à Kinshasa.

## Fonctionnalités
- Catalogue dynamique de cartes cadeaux.
- Paiement simulé via M-Pesa, Orange Money, Airtel Money, PayPal et carte de crédit.
- Mention explicite du délai de livraison: **30 minutes max**.
- Stock des codes en SQLite.
- Après confirmation: attribution automatique d'un code + envoi email.

## Fusion avec `kinshasa-gift-hub`
La fusion distante automatique nécessite un accès réseau GitHub.

### Option A (recommandée) — merge Git direct
```bash
git remote add kgh https://github.com/Brummelmayano/kinshasa-gift-hub.git
git fetch kgh
git merge kgh/main --allow-unrelated-histories
```

### Option B — import des codes exportés
1. Exporter un JSON depuis `kinshasa-gift-hub`.
2. Importer dans cette base:
```bash
python scripts/merge_kinshasa_gift_hub.py --input kinshasa-gift-hub-export.json --db giftcards.db
```

Format JSON attendu:
```json
{
  "gift_codes": [
    {"product_id": "netflix", "code": "NETFLIX-1234-KIN"}
  ]
}
```

## Stack technique
- Backend: Python standard library (WSGI) + SQLite.
- Frontend: HTML/CSS/JS.
- Tests: pytest.

## Lancer l'application
```bash
python app.py
```
Puis ouvrir `http://localhost:5000`.

## Dépendances
```bash
pip install -r requirements.txt
```

## Variables email SMTP (optionnel)
- `MAIL_SENDER`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`

Sans SMTP, les emails sont enregistrés dans `sent_emails.log`.

## Tests
```bash
pytest -q
```
