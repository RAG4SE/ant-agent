// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./IDataStorage.sol";
import "hardhat/console.sol";

/**
 * @title DataManager
 * @dev Main contract that manages multiple DataStorage contracts and calls their interface functions
 */
contract DataManager {

    struct StorageInfo {
        IDataStorage storageContract;
        string name;
        bool isActive;
    }

    IDataStorage storageContract;

    StorageInfo si;

    // Mapping of storage contract IDs to their info
    mapping(uint256 => StorageInfo) private storages;

    // Array of storage IDs
    uint256[] private storageIds;

    // Counter for storage IDs
    uint256 private storageCounter;

    // Owner of the DataManager
    address public owner;

    // Events
    event StorageAdded(uint256 indexed storageId, string name, address indexed storageAddress);
    event StorageRemoved(uint256 indexed storageId);
    event DataStoredInStorage(uint256 indexed storageId, string key, string value);
    event DataRetrievedFromStorage(uint256 indexed storageId, string key, string value);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    constructor() {
        owner = msg.sender;
        storageCounter = 0;
    }

    /**
     * @dev Adds a new DataStorage contract to be managed
     * @param storageAddress Address of the DataStorage contract
     * @param name Human-readable name for this storage
     * @return storageId The ID assigned to this storage
     */
    function addStorage(address storageAddress, string calldata name) external onlyOwner returns (uint256 storageId) {
        require(storageAddress != address(0), "Invalid storage address");
        require(bytes(name).length > 0, "Storage name cannot be empty");

        storageId = ++storageCounter;

        storages[storageId] = StorageInfo({
            storageContract: IDataStorage(storageAddress),
            name: name,
            isActive: true
        });

        storageIds.push(storageId);

        emit StorageAdded(storageId, name, storageAddress);
        return storageId;
    }

    /**
     * @dev Removes a storage contract from management
     * @param storageId The ID of the storage to remove
     */
    function removeStorage(uint256 storageId) external onlyOwner {
        require(storages[storageId].isActive, "Storage not found or inactive");

        storages[storageId].isActive = false;

        // Remove from storageIds array
        for (uint256 i = 0; i < storageIds.length; i++) {
            if (storageIds[i] == storageId) {
                storageIds[i] = storageIds[storageIds.length - 1];
                storageIds.pop();
                break;
            }
        }

        emit StorageRemoved(storageId);
    }

    /**
     * @dev Stores data in a specific storage contract by calling its interface function
     * @param storageId The ID of the storage to use
     * @param key The key to store data under
     * @param value The value to store
     * @return success Whether the operation was successful
     */
    function storeDataInStorage(uint256 storageId, string calldata key, string calldata value)
        external
        returns (bool success)
    {
        // require(storages[storageId].isActive, "Storage not found or inactive");
        // require(bytes(key).length > 0, "Key cannot be empty");
        // require(bytes(value).length > 0, "Value cannot be empty");

        // Call the interface function from the storage contract
        // IDataStorage.storeData() - See IDataStorage.sol:15
        // console.log("Storing data for storage ID:", storageId);
        bool result = storages[storageId].storageContract.storeData(key, value);
        // bool result2 = storageContract.storeData(key, value);
        // bool result3 = si.storageContract.storeData(key, value);

        // if (result) {
        //     emit DataStoredInStorage(storageId, key, value);
        // }

        return result;
    }

    /**
     * @dev Retrieves data from a specific storage contract by calling its interface function
     * @param storageId The ID of the storage to retrieve from
     * @param key The key to retrieve data for
     * @return value The retrieved value
     */
    function getDataFromStorage(uint256 storageId, string calldata key)
        external
        view
        returns (string memory value)
    {
        require(storages[storageId].isActive, "Storage not found or inactive");

        // Call the interface function from the storage contract
        // IDataStorage.getData() - See IDataStorage.sol:22
        return storages[storageId].storageContract.getData(key);
    }

    /**
     * @dev Updates data in a specific storage contract by calling its interface function
     * @param storageId The ID of the storage to update
     * @param key The key to update
     * @param newValue The new value to set
     * @return success Whether the operation was successful
     */
    function updateDataInStorage(uint256 storageId, string calldata key, string calldata newValue)
        external
        returns (bool success)
    {
        require(storages[storageId].isActive, "Storage not found or inactive");

        // Call the interface function from the storage contract
        // IDataStorage.updateData() - See IDataStorage.sol:30
        bool result = storages[storageId].storageContract.updateData(key, newValue);

        if (result) {
            emit DataStoredInStorage(storageId, key, newValue);
        }

        return result;
    }

    /**
     * @dev Deletes data from a specific storage contract by calling its interface function
     * @param storageId The ID of the storage to delete from
     * @param key The key to delete
     * @return success Whether the operation was successful
     */
    function deleteDataFromStorage(uint256 storageId, string calldata key)
        external
        onlyOwner
        returns (bool success)
    {
        require(storages[storageId].isActive, "Storage not found or inactive");

        // Call the interface function from the storage contract
        // IDataStorage.deleteData() - See IDataStorage.sol:37
        return storages[storageId].storageContract.deleteData(key);
    }

    /**
     * @dev Gets the item count from a specific storage contract by calling its interface function
     * @param storageId The ID of the storage to query
     * @return count The total count of items in the storage
     */
    function getItemCountFromStorage(uint256 storageId) external view returns (uint256 count) {
        require(storages[storageId].isActive, "Storage not found or inactive");

        // Call the interface function from the storage contract
        // IDataStorage.getItemCount() - See IDataStorage.sol:43
        return storages[storageId].storageContract.getItemCount();
    }

    /**
     * @dev Batch operation: stores the same data in multiple storages
     * @param storageIds Array of storage IDs to store data in
     * @param key The key to store data under
     * @param value The value to store
     * @return results Array of boolean results for each storage
     */
    function batchStoreData(uint256[] calldata storageIds, string calldata key, string calldata value)
        external
        returns (bool[] memory results)
    {
        results = new bool[](storageIds.length);

        for (uint256 i = 0; i < storageIds.length; i++) {
            if (storages[storageIds[i]].isActive) {
                // Call the interface function from each storage contract
                // IDataStorage.storeData() - See IDataStorage.sol:15
                results[i] = storages[storageIds[i]].storageContract.storeData(key, value);

                if (results[i]) {
                    emit DataStoredInStorage(storageIds[i], key, value);
                }
            }
        }

        return results;
    }

    /**
     * @dev Gets information about a storage
     * @param storageId The ID of the storage
     * @return name The name of the storage
     * @return storageAddress The address of the storage contract
     * @return isActive Whether the storage is active
     */
    function getStorageInfo(uint256 storageId)
        external
        view
        returns (string memory name, address storageAddress, bool isActive)
    {
        StorageInfo storage storageInfo = storages[storageId];
        return (storageInfo.name, address(storageInfo.storageContract), storageInfo.isActive);
    }

    /**
     * @dev Gets all active storage IDs
     * @return activeStorageIds Array of active storage IDs
     */
    function getActiveStorageIds() external view returns (uint256[] memory activeStorageIds) {
        uint256 activeCount = 0;

        // Count active storages
        for (uint256 i = 0; i < storageIds.length; i++) {
            if (storages[storageIds[i]].isActive) {
                activeCount++;
            }
        }

        // Create result array
        activeStorageIds = new uint256[](activeCount);
        uint256 index = 0;

        // Fill result array
        for (uint256 i = 0; i < storageIds.length; i++) {
            if (storages[storageIds[i]].isActive) {
                activeStorageIds[index] = storageIds[i];
                index++;
            }
        }

        return activeStorageIds;
    }
}