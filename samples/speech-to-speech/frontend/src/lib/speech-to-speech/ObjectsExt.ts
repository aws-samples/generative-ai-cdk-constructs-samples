/**
 * Utility functions for object operations
 */

class ObjectExt {
  /**
   * Check if an object exists (not null or undefined)
   * @param obj - The object to check
   * @returns True if the object exists, false otherwise
   */
  static exists(obj: any): boolean {
    return obj !== null && obj !== undefined;
  }
}

export default ObjectExt;
