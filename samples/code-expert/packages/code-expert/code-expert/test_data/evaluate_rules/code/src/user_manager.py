#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

class UserManager:
    def __init__(self, database):
        self.database = database

    def create_user(self, username, email):
        try:
            self.database.insert({"username": username, "email": email})
        except DatabaseError as e:
            raise UserCreationError(f"Failed to create user: {str(e)}")

    def delete_user(self, user_id):
        try:
            self.database.delete(user_id)
        except DatabaseError as e:
            raise UserDeletionError(f"Failed to delete user: {str(e)}")
