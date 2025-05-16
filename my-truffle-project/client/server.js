const express = require('express');
const bodyParser = require('body-parser');
const mysql = require('mysql2'); // Pour la connexion à MySQL

const app = express();
app.use(bodyParser.json()); // Pour analyser le corps de la requête en JSON

// Configuration de la connexion MySQL
const db = mysql.createConnection({
    host: 'localhost',
    user: 'root',          // Ton utilisateur MySQL
    password: '',          // Ton mot de passe MySQL
    database: 'oliveoil' // Remplace par le nom de ta base de données
});

db.connect((err) => {
    if (err) {
        console.error('Erreur de connexion à la base de données:', err);
    } else {
        console.log('Connexion à la base de données MySQL réussie.');
    }
});

// Endpoint pour recevoir les résultats de la détection
app.post('/api/save-detection', (req, res) => {
    const { date, image_url, insectes } = req.body;

    // Pour chaque insecte détecté, on l'enregistre dans la base de données
    insectes.forEach(insecte => {
        const { nom, statut } = insecte;

        // SQL pour insérer les données dans la table insect_detection
        const query = `
            INSERT INTO insect_detection (date, image_url, insecte_name, statut)
            VALUES (?, ?, ?, ?)
        `;

        const values = [date, image_url, nom, statut];

        // Exécution de la requête
        db.query(query, values, (err, result) => {
            if (err) {
                console.error('Erreur lors de l\'insertion dans la base de données:', err);
                return;
            }
            console.log('Résultat inséré avec succès dans la base de données:', result);
        });
    });

    // Réponse à l'API
    res.status(200).send({ message: 'Detection results saved successfully.' });
});

// Démarrer le serveur
app.listen(3000, () => {
    console.log('Server Node.js is running on port 3000');
});
