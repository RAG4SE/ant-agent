// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * @title IDataStorage
 * @dev Interface for data storage operations
 */
interface IDataStorage {
    /**
     * @dev Stores data with a key
     * @param key The key to store data under
     * @param value The value to store
     * @return success Whether the operation was successful
     */
    function storeData(string calldata key, string calldata value) external returns (bool success);

    /**
     * @dev Retrieves data by key
     * @param key The key to retrieve data for
     * @return value The stored value
     */
    function getData(string calldata key) external view returns (string memory value);

    /**
     * @dev Updates existing data
     * @param key The key to updatehard
     * @param newValue The new value to set
     * @return success Whether the operation was successful
     */
    function updateData(string calldata key, string calldata newValue) external returns (bool success);

    /**
     * @dev Deletes data by key
     * @param key The key to delete
     * @return success Whether the operation was successful
     */
    function deleteData(string calldata key) external returns (bool success);

    /**
     * @dev Gets the total number of stored items
     * @return count The total count
     */
    function getItemCount() external view returns (uint256 count);
}