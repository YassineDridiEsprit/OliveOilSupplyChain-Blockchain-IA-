const OliveOilProductionChain = artifacts.require("OliveOilProductionChain");

contract("OliveOilProductionChain", accounts => {
  let instance;
  let batchId;

  before(async () => {
    instance = await OliveOilProductionChain.deployed();
  });

  describe("Batch Creation", () => {
    it("should create a batch and return valid batchId", async () => {
      const tx = await instance.createBatch("Ali", "10-Apr-2025", "Crete, Greece", "Hand-picked, Organic");
      batchId = tx.logs[0].args.batchId.toNumber();
      
      assert.isNumber(batchId, "Should return a valid batch ID");
      assert.equal(batchId, 0, "First batch should have ID 0");
    });

    it("should increment batch count", async () => {
      const count = await instance.getBatchCount();
      assert.equal(count, 1, "Batch count should be 1 after creation");
    });
  });

  describe("getBatch Function", () => {
    it("should return correct harvesting data", async () => {
      const batch = await instance.getBatch(batchId);
      
      assert.equal(batch.harvesting.farmer, "Ali", "Farmer name mismatch");
      assert.equal(batch.harvesting.date, "10-Apr-2025", "Harvest date mismatch");
      assert.equal(batch.harvesting.location, "Crete, Greece", "Location mismatch");
      assert.equal(batch.harvesting.method, "Hand-picked, Organic", "Method mismatch");
    });

    it("should return default values for unset fields", async () => {
      const batch = await instance.getBatch(batchId);
      
      assert.equal(batch.transportation.vehicleType, "", "Transportation should be empty");
      assert.equal(batch.pressingProcess.operatorName, "", "Pressing process should be empty");
      assert.equal(batch.qualityCheck.lab, "", "Quality check should be empty");
      assert.isFalse(batch.isFinalized, "Batch should not be finalized initially");
    });

    it("should revert for non-existent batch", async () => {
      try {
        await instance.getBatch(999);
        assert.fail("Should have reverted for non-existent batch");
      } catch (error) {
        assert.include(error.message, "Batch does not exist", "Should revert with correct message");
      }
    });
  });

  describe("Batch Processing", () => {
    it("should log transportation info", async () => {
      await instance.logTransportation(batchId, 4, "18°C", "T-101", "Refrigerated Van");
      const batch = await instance.getBatch(batchId);
      
      assert.equal(batch.transportation.vehicleType, "Refrigerated Van");
      assert.equal(batch.transportation.duration, 4);
    });

    it("should log quality check and format values", async () => {
      await instance.logQualityCheck(batchId, "OrganoLab", 25, 92, true);
      
      const batch = await instance.getBatch(batchId);
      assert.equal(batch.qualityCheck.lab, "OrganoLab");
      
      const acidity = await instance.getAcidity(batchId);
      const peroxide = await instance.getPeroxideValue(batchId);
      assert.equal(acidity, "0.25");
      assert.equal(peroxide, "9.2");
    });

    it("should finalize batch", async () => {
      await instance.finalizeBatch(batchId);
      const batch = await instance.getBatch(batchId);
      assert.isTrue(batch.isFinalized);
    });
  });

});