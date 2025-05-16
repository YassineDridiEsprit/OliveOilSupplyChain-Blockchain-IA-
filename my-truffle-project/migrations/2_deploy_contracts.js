const OliveOilChain = artifacts.require("OliveOilProductionChain");

module.exports = function (deployer) {
  deployer.deploy(OliveOilChain);
}