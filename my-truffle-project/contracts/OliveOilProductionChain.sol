// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";

contract OliveOilProductionChain is AccessControl {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant FARMER_ROLE = keccak256("FARMER_ROLE");
    bytes32 public constant TRANSPORTER_ROLE = keccak256("TRANSPORTER_ROLE");
    bytes32 public constant PRESSING_ROLE = keccak256("PRESSING_ROLE");
    bytes32 public constant ONH_ROLE = keccak256("ONH_ROLE");

    struct Harvesting {
        string farmer;
        string date;
        string location;
        string method;
        uint256 quantity;
        string variety;  
    }

    struct Transportation {
        uint duration;
        string conditions;
        string transporterId;
        string vehicleType;
    }

    struct StorageBeforePressing {
        uint duration;
        string pressingId;
        string conditions;
        uint temperature;
        uint humidity;
        uint goodOlives; 
        uint badOlives;  
    }

    struct PressingProcess {
        string date;
        string pressingId;
        string facility;
        string method;
        string conditions;
        uint256 temperature;
        uint256 pressure;
        string operatorName;
    }

    struct StorageAfterPressing {
        string tankId;
        string pressingId;
        uint duration;
        string conditions;
        uint256 temperature;
        uint256 humidity;
        bool inertAtmosphere;
    }

    struct QualityCheck {
        string lab;
        string onhId;
        uint256 acidity;
        string quality;
        string area;
        uint256 peroxideValue;
        bool certifiedOrganic;
    }

    struct Batch {
        Harvesting harvesting;
        Transportation transportation;
        StorageBeforePressing storageBeforePressing;
        PressingProcess pressingProcess;
        StorageAfterPressing storageAfterPressing;
        QualityCheck qualityCheck;
        bool isFinalized;
    }

    Batch[] public batches;
    mapping(address => uint[]) public farmerBatches;

    event NewBatch(uint256 batchId);
    event FinalizedBatch(uint256 batchId);

    constructor() {
        _setupRole(DEFAULT_ADMIN_ROLE, 0xb83AAbF4a4679A86f988837Ca87be8dd05390698);
        _setupRole(ADMIN_ROLE, 0xb83AAbF4a4679A86f988837Ca87be8dd05390698);
        _setupRole(FARMER_ROLE, 0x013e8AaE064294cf146d5743076e8f11CF4489F9);
        _setupRole(TRANSPORTER_ROLE, 0x06Fdc58AF6750D6180F11EA31cD9eA077b19aCb7);
        _setupRole(PRESSING_ROLE, 0xf91aCf0Fb5384945c2F82f404f7f5C1856f779cA);
        _setupRole(ONH_ROLE, 0x25A1d99D5810568D9582dBF764200D499D65D5fd);
    }

    function createBatch(
        string memory farmer,
        string memory harvestDate,
        string memory location,
        string memory method,
        uint256 quantity,
        string memory variety
    ) public onlyRole(FARMER_ROLE) returns (uint256 batchId) {
        batchId = batches.length;
        batches.push(
            Batch({
                harvesting: Harvesting(farmer, harvestDate, location, method, quantity, variety),
                transportation: Transportation(0, "", "", ""),
                storageBeforePressing: StorageBeforePressing(0, "", "", 0, 0, 0, 0), // Initialized with 0 for goodOlives and badOlives
                pressingProcess: PressingProcess("", "", "", "", "", 0, 0, ""),
                storageAfterPressing: StorageAfterPressing("", "", 0, "", 0, 0, false),
                qualityCheck: QualityCheck("", "", 0, "", "", 0, false),
                isFinalized: false
            })
        );
        farmerBatches[msg.sender].push(batchId);
        emit NewBatch(batchId);
    }

    function logTransportation(
        uint256 batchId,
        uint duration,
        string memory conditions,
        string memory transporterId,
        string memory vehicleType
    ) public onlyRole(TRANSPORTER_ROLE) {
        require(batchId < batches.length, "Batch does not exist");
        require(bytes(batches[batchId].transportation.transporterId).length == 0, "Batch already transported");
        batches[batchId].transportation = Transportation(duration, conditions, transporterId, vehicleType);
    }

    function logStorageBeforePressing(
        uint256 batchId,
        string memory pressingId,
        uint duration,
        string memory conditions,
        uint temperature,
        uint humidity,
        uint goodOlives,  // Added parameter
        uint badOlives    // Added parameter
    ) public onlyRole(PRESSING_ROLE) {
        require(batchId < batches.length, "Batch does not exist");
        batches[batchId].storageBeforePressing = StorageBeforePressing(duration, pressingId, conditions, temperature, humidity, goodOlives, badOlives);
    }

    function logPressingProcess(
        uint256 batchId,
        string memory pressingId,
        string memory date,
        string memory facility,
        string memory method,
        string memory conditions,
        uint temperature,
        uint pressure,
        string memory operatorName
    ) public onlyRole(PRESSING_ROLE) {
        require(batchId < batches.length, "Batch does not exist");
        batches[batchId].pressingProcess = PressingProcess(date, pressingId, facility, method, conditions, temperature, pressure, operatorName);
    }

    function logStorageAfterPressing(
        uint256 batchId,
        string memory pressingId,
        string memory tankId,
        uint duration,
        string memory conditions,
        uint temperature,
        uint humidity,
        bool inertAtmosphere
    ) public onlyRole(PRESSING_ROLE) {
        require(batchId < batches.length, "Batch does not exist");
        batches[batchId].storageAfterPressing = StorageAfterPressing(tankId, pressingId, duration, conditions, temperature, humidity, inertAtmosphere);
    }

    function logQualityCheck(
        uint256 batchId,
        string memory onhId,
        string memory lab,
        uint acidityScaled,
        string memory quality,  // Added parameter
        string memory area,     // Added parameter
        uint peroxideValueScaled,
        bool certifiedOrganic
    ) public onlyRole(ONH_ROLE) {
        require(batchId < batches.length, "Batch does not exist");
        batches[batchId].isFinalized = true;
        batches[batchId].qualityCheck = QualityCheck(lab, onhId, acidityScaled, quality, area, peroxideValueScaled, certifiedOrganic);
        emit FinalizedBatch(batchId);
    }

    function getBatch(uint256 batchId) public view returns (Batch memory) {
        require(batchId < batches.length, "Batch does not exist");
        return batches[batchId];
    }

    function getHarvestDetails(uint256 batchId) public view returns (
        string memory farmer,
        string memory date,
        string memory location,
        string memory method
    ) {
        require(batchId < batches.length, "Batch does not exist");
        Harvesting memory h = batches[batchId].harvesting;
        return (h.farmer, h.date, h.location, h.method);
    }

    function assignFarmerRole(address account) public onlyRole(ADMIN_ROLE) {
        grantRole(FARMER_ROLE, account);
    }

    function assignTransporterRole(address account) public onlyRole(ADMIN_ROLE) {
        grantRole(TRANSPORTER_ROLE, account);
    }

    function revokeFarmerRole(address account) public onlyRole(ADMIN_ROLE) {
        revokeRole(FARMER_ROLE, account);
    }

    function revokeTransporterRole(address account) public onlyRole(ADMIN_ROLE) {
        revokeRole(TRANSPORTER_ROLE, account);
    }

    function getBatchCount() public view returns (uint) {
        return batches.length;
    }

    function getBatchesByFarmer(address farmer) public view returns (uint[] memory) {
        return farmerBatches[farmer];
    }

    function getAcidity(uint256 batchId) public view returns (string memory) {
        uint acidityScaled = batches[batchId].qualityCheck.acidity;
        return string(abi.encodePacked(uint2str(acidityScaled / 100), ".", uint2str(acidityScaled % 100)));
    }

    function getPeroxideValue(uint256 batchId) public view returns (string memory) {
        uint peroxideValueScaled = batches[batchId].qualityCheck.peroxideValue;
        return string(abi.encodePacked(uint2str(peroxideValueScaled / 10), ".", uint2str(peroxideValueScaled % 10)));
    }

    function uint2str(uint _i) internal pure returns (string memory) {
        if (_i == 0) return "0";
        uint j = _i;
        uint len;
        while (j != 0) {
            len++;
            j /= 10;
        }
        bytes memory bstr = new bytes(len);
        uint k = len;
        while (_i != 0) {
            bstr[--k] = bytes1(uint8(48 + _i % 10));
            _i /= 10;
        }
        return string(bstr);
    }

    function getBatchesByTransporter(string memory transporterId) public view returns (uint[] memory) {
        uint count = 0;
        for (uint i = 0; i < batches.length; i++) {
            if (keccak256(bytes(batches[i].transportation.transporterId)) == keccak256(bytes(transporterId))) {
                count++;
            }
        }
        uint[] memory result = new uint[](count);
        uint index = 0;
        for (uint i = 0; i < batches.length; i++) {
            if (keccak256(bytes(batches[i].transportation.transporterId)) == keccak256(bytes(transporterId))) {
                result[index] = i;
                index++;
            }
        }
        return result;
    }

    function getBatchesByPressingId(string memory pressingId) public view returns (uint[] memory) {
        uint count = 0;
        for (uint i = 0; i < batches.length; i++) {
            if (keccak256(bytes(batches[i].storageBeforePressing.pressingId)) == keccak256(bytes(pressingId))) {
                count++;
            }
        }

        uint[] memory result = new uint[](count);
        uint index = 0;
        for (uint i = 0; i < batches.length; i++) {
            if (keccak256(bytes(batches[i].storageBeforePressing.pressingId)) == keccak256(bytes(pressingId))) {
                result[index] = i;
                index++;
            }
        }

        return result;
    }

    function getBatchesByOnhId(string memory onhId) public view returns (uint[] memory) {
        uint count = 0;
        for (uint i = 0; i < batches.length; i++) {
            if (keccak256(bytes(batches[i].qualityCheck.onhId)) == keccak256(bytes(onhId))) {
                count++;
            }
        }
        
        uint[] memory result = new uint[](count);
        uint index = 0;
        for (uint i = 0; i < batches.length; i++) {
            if (keccak256(bytes(batches[i].qualityCheck.onhId)) == keccak256(bytes(onhId))) {
                result[index] = i;
                index++;
            }
        }

        return result;
    }
}