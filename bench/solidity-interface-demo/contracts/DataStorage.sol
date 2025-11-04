// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./IDataStorage.sol";

/**
 * @title DataStorage
 * @dev Implementation of IDataStorage interface for storing and managing key-value data
 */
contract DataStorage is IDataStorage {

    struct DataItem {
        string value;
        bool exists;
        uint256 timestamp;
    }

    // Mapping from string keys to DataItem
    mapping(string => DataItem) private data;

    // Array to keep track of all keys for counting
    string[] private keys;

    // Owner address for access control
    address public owner;

    // Events for logging operations
    event DataStored(string indexed key, string value, address indexed storedBy);
    event DataUpdated(string indexed key, string newValue, address indexed updatedBy);
    event DataDeleted(string indexed key, address indexed deletedBy);

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Stores data with a key
     */
    function storeData(string calldata key, string calldata value) external override returns (bool success) {
        // require(bytes(key).length > 0, "Key cannot be empty");
        require(bytes(value).length > 0, "Value cannot be empty");

        if (!data[key].exists) {
            keys.push(key);
        }

        data[key] = DataItem({
            value: value,
            exists: true,
            timestamp: block.timestamp
        });

        emit DataStored(key, value, msg.sender);
        return true;
    }

    /**
     * @dev Retrieves data by key
     */
    function getData(string calldata key) external view override returns (string memory value) {
        require(data[key].exists, "Key does not exist");
        return data[key].value;
    }

    /**
     * @dev Updates existing data
     */
    function updateData(string calldata key, string calldata newValue) external override returns (bool success) {
        require(data[key].exists, "Key does not exist");
        require(bytes(newValue).length > 0, "New value cannot be empty");

        data[key].value = newValue;
        data[key].timestamp = block.timestamp;

        emit DataUpdated(key, newValue, msg.sender);
        return true;
    }

    /**
     * @dev Deletes data by key
     */
    function deleteData(string calldata key) external override returns (bool success) {
        require(data[key].exists, "Key does not exist");
        require(msg.sender == owner, "Only owner can delete data");

        // Remove from mapping
        delete data[key];

        // Remove from keys array (by replacing with last element and popping)
        for (uint256 i = 0; i < keys.length; i++) {
            if (keccak256(bytes(keys[i])) == keccak256(bytes(key))) {
                keys[i] = keys[keys.length - 1];
                keys.pop();
                break;
            }
        }

        emit DataDeleted(key, msg.sender);
        return true;
    }

    /**
     * @dev Gets the total number of stored items
     */
    function getItemCount() external view override returns (uint256 count) {
        return keys.length;
    }

    /**
     * @dev Additional helper function to check if a key exists
     */
    function keyExists(string calldata key) external view returns (bool exists) {
        return data[key].exists;
    }

    /**
     * @dev Gets the timestamp when data was last modified
     */
    function getDataTimestamp(string calldata key) external view returns (uint256 timestamp) {
        require(data[key].exists, "Key does not exist");
        return data[key].timestamp;
    }
}