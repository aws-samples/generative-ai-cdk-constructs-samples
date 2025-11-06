//
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
// with the License. A copy of the License is located at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
// OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
// and limitations under the License.
//

import { useState, useCallback } from 'react';
import {
  getGuidelines,
  createGuideline,
  updateGuideline,
  deleteGuideline
} from '@lib/api';
import { getErrorMessage } from '@lib/utils';
import type {
  Guideline,
  GuidelinesListResponse,
  GuidelineFormData,
  GuidelinesFilters
} from '@lib/types';

interface UseGuidelinesState {
  guidelines: Guideline[];
  loading: boolean;
  error: string | null;
  lastEvaluatedKey?: string;
  totalCount?: number;
}

interface UseGuidelinesReturn extends UseGuidelinesState {
  loadGuidelines: (contractTypeId: string, filters?: Partial<GuidelinesFilters>) => Promise<void>;
  createNewGuideline: (contractTypeId: string, data: GuidelineFormData) => Promise<Guideline>;
  updateExistingGuideline: (contractTypeId: string, clauseTypeId: string, updates: Partial<Omit<GuidelineFormData, 'clauseTypeId'>>) => Promise<Guideline>;
  deleteExistingGuideline: (contractTypeId: string, clauseTypeId: string) => Promise<void>;
  clearError: () => void;
  refreshGuidelines: () => Promise<void>;
}

export function useGuidelines(): UseGuidelinesReturn {
  const [state, setState] = useState<UseGuidelinesState>({
    guidelines: [],
    loading: false,
    error: null,
    lastEvaluatedKey: undefined,
    totalCount: undefined,
  });

  // Store current filters for refresh functionality
  const [currentFilters, setCurrentFilters] = useState<{
    contractTypeId: string;
    filters?: Partial<GuidelinesFilters>;
  } | null>(null);

  const setLoading = useCallback((loading: boolean) => {
    setState(prev => ({ ...prev, loading }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error }));
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, [setError]);

  const handleError = useCallback((error: unknown) => {
    const errorMessage = getErrorMessage(error);
    console.error('Guidelines operation failed:', errorMessage);
    setError(errorMessage);
  }, [setError]);

  const loadGuidelines = useCallback(async (
    contractTypeId: string,
    filters?: Partial<GuidelinesFilters>
  ) => {
    try {
      setLoading(true);
      setError(null);

      // Store current parameters for refresh
      setCurrentFilters({ contractTypeId, filters });

      const options = {
        search: filters?.search,
        level: filters?.level && filters.level !== '' ? filters.level : undefined,
        limit: 50, // Default limit
      };

      const response: GuidelinesListResponse = await getGuidelines(contractTypeId, options);

      setState(prev => ({
        ...prev,
        guidelines: response.guidelines,
        lastEvaluatedKey: response.lastEvaluatedKey,
        totalCount: response.totalCount,
        loading: false,
      }));
    } catch (error) {
      handleError(error);
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [setLoading, setError, handleError]);

  const createNewGuideline = useCallback(async (
    contractTypeId: string,
    data: GuidelineFormData
  ): Promise<Guideline> => {
    try {
      setLoading(true);
      setError(null);

      const newGuideline = await createGuideline(contractTypeId, data);
      console.log('Created guideline:', newGuideline);

      // Reload guidelines from backend to ensure fresh data
      if (currentFilters) {
        await loadGuidelines(currentFilters.contractTypeId, currentFilters.filters);
      }

      return newGuideline;
    } catch (error) {
      console.error('Error creating guideline:', error);
      handleError(error);
      setState(prev => ({ ...prev, loading: false }));
      throw error;
    }
  }, [setLoading, setError, handleError, currentFilters, loadGuidelines]);

  const updateExistingGuideline = useCallback(async (
    contractTypeId: string,
    clauseTypeId: string,
    updates: Partial<Omit<GuidelineFormData, 'clauseTypeId'>>
  ): Promise<Guideline> => {
    try {
      setLoading(true);
      setError(null);

      const updatedGuideline = await updateGuideline(contractTypeId, clauseTypeId, updates);

      // Reload guidelines from backend to ensure fresh data
      if (currentFilters) {
        await loadGuidelines(currentFilters.contractTypeId, currentFilters.filters);
      }

      return updatedGuideline;
    } catch (error) {
      handleError(error);
      setState(prev => ({ ...prev, loading: false }));
      throw error;
    }
  }, [setLoading, setError, handleError, currentFilters, loadGuidelines]);

  const deleteExistingGuideline = useCallback(async (
    contractTypeId: string,
    clauseTypeId: string
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await deleteGuideline(contractTypeId, clauseTypeId);

      // Reload guidelines from backend to ensure fresh data
      if (currentFilters) {
        await loadGuidelines(currentFilters.contractTypeId, currentFilters.filters);
      }
    } catch (error) {
      handleError(error);
      setState(prev => ({ ...prev, loading: false }));
      throw error;
    }
  }, [setLoading, setError, handleError, currentFilters, loadGuidelines]);

  const refreshGuidelines = useCallback(async () => {
    if (currentFilters) {
      await loadGuidelines(currentFilters.contractTypeId, currentFilters.filters);
    }
  }, [currentFilters, loadGuidelines]);

  return {
    ...state,
    loadGuidelines,
    createNewGuideline,
    updateExistingGuideline,
    deleteExistingGuideline,
    clearError,
    refreshGuidelines,
  };
}