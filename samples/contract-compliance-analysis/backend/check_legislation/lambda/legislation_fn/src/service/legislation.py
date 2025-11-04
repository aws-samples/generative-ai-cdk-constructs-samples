#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

from typing import List

from aws_lambda_powertools import Logger

from repository import LegislationRepository
from model import Legislation

logger = Logger()

class LegislationApi:
  def __init__(self, legislation_repository: LegislationRepository) -> None:
    self.legislation_repository = legislation_repository

  def list_legislations(self) -> List[Legislation]:
    """
    Lists all legislations persisted in the db
    """
    legislations = self.legislation_repository.list_legislations()
    logger.info(f"Retrieved indexed legislations: {legislations} from knowledge base")
    return legislations


  def ingest_legislation(self, legislation: Legislation) -> None:
    """
    Ingests a legislation document into the repository given an id, name and s3 key
    """
    self.legislation_repository.ingest_legislation(legislation)