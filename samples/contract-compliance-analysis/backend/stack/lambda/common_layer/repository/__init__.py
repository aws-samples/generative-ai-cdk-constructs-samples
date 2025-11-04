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

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from model import Job, Workflow, Clause, ContractType, Guideline, ImportJob
from schema import StartWorkflowRequest

class JobsRepository(ABC):

  @abstractmethod
  def record_job(self, job: Job) -> None:
    ...

  @abstractmethod
  def get_jobs(self, contract_type_id: Optional[str] = None) -> List[Job]:
    ...

  @abstractmethod
  def get_job(self, job_id: str) -> Job:
    ...

class ClausesRepository(ABC):

  @abstractmethod
  def get_clauses(self, job_id: str) -> List[Clause]:
    ...

class WorkflowsRepository(ABC):

  @abstractmethod
  def start_execution(self, request: StartWorkflowRequest) -> str:
    ...

  @abstractmethod
  def get_state_machine_execution_details(self, workflow_id: str) -> Workflow:
    ...

class ContractTypeRepository(ABC):

  @abstractmethod
  def create_contract_type(self, contract_type: ContractType) -> None:
    ...

  @abstractmethod
  def get_contract_types(self) -> List[ContractType]:
    ...

  @abstractmethod
  def get_contract_type(self, contract_type_id: str) -> ContractType:
    ...

  @abstractmethod
  def update_contract_type(self, contract_type: ContractType) -> None:
    ...

  @abstractmethod
  def delete_contract_type(self, contract_type_id: str) -> None:
    ...


class GuidelinesRepository(ABC):

  @abstractmethod
  def list_guidelines(self, contract_type_id: str, search: Optional[str] = None,
                     level: Optional[str] = None, limit: int = 50,
                     last_evaluated_key: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """List guidelines with filtering and pagination"""
    ...

  @abstractmethod
  def get_guideline(self, contract_type_id: str, clause_type_id: str) -> Optional[Guideline]:
    """Get specific guideline"""
    ...

  @abstractmethod
  def create_guideline(self, guideline: Guideline) -> Guideline:
    """Create new guideline with timestamps"""
    ...

  @abstractmethod
  def update_guideline(self, contract_type_id: str, clause_type_id: str,
                      updates: Dict[str, Any]) -> Guideline:
    """Update existing guideline"""
    ...

  @abstractmethod
  def delete_guideline(self, contract_type_id: str, clause_type_id: str) -> bool:
    """Delete guideline"""
    ...

  @abstractmethod
  def delete_all_guidelines_for_contract_type(self, contract_type_id: str) -> int:
    """Delete all guidelines for a specific contract type"""
    ...


class ImportJobsRepository(ABC):

  @abstractmethod
  def create_import_job(self, import_job: ImportJob) -> None:
    """Create a new import job"""
    ...

  @abstractmethod
  def get_import_job(self, import_job_id: str) -> Optional[ImportJob]:
    """Get a specific import job by ID"""
    ...

  @abstractmethod
  def update_import_job(self, import_job: ImportJob) -> None:
    """Update an existing import job"""
    ...

  @abstractmethod
  def update_import_job_status(self, import_job_id: str, status: str,
                              error_message: Optional[str] = None,
                              progress: Optional[int] = None,
                              current_step: Optional[str] = None,
                              contract_type_id: Optional[str] = None) -> None:
    """Update import job status and related fields"""
    ...