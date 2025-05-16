const express = require('express');
const Web3 = require('web3').default;
const contract = require('../build/contracts/OliveOilProductionChain.json');
const app = express();
app.use(express.json());

// Connect to local Ganache
const web3 = new Web3("http://127.0.0.1:7545");

// Replace with your deployed contract address and account
const contractAddress = "0x2332d097f383dA19683235ce4cBbafb7D757ddB2";
const account = "0x013e8AaE064294cf146d5743076e8f11CF4489F9";

const instance = new web3.eth.Contract(contract.abi, contractAddress);

// test cnx 
app.post('/cnx', async (req,res) => {
    //res.status(200).send('Succeeded');
    res.status(200).json({ status: 'success', message: 'cnx successfully' });
});
// Sample route: Create Batch
app.post('/create-batch', async (req, res) => {
    try {
        const { farmer, harvestDate, location, method } = req.body;

        const receipt = await instance.methods.createBatch(farmer, harvestDate, location, method)
            .send({ from: account, gas: 5000000 });

        // Get the batchId from the emitted event (NewBatch)
        const event = receipt.events.NewBatch;
        const batchId = event.returnValues.batchId.toString();  // Convert BigInt to string

        res.json({ status: 'success', message: 'Batch created successfully', batchId: batchId });
    } catch (err) {
        console.error(err);
        res.status(500).json({ status: 'error', error: err.message });
    }
});


app.listen(5000, () => {
    console.log("API server running on http://localhost:5000");
});
