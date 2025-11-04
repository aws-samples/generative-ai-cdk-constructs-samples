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

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  SearchIcon,
  FilterIcon,
  XIcon,
  RefreshCcwIcon,
} from "lucide-react";
import { IMPACT_COLORS } from "@/lib/constants";
import { useTranslation } from "react-i18next";
import type { ContractType, ImpactLevel } from "@/lib/types";

interface GuidelinesFiltersProps {
  searchTerm: string;
  onSearchChange: (search: string) => void;
  levelFilter: string;
  onLevelFilterChange: (level: string) => void;
  contractTypeId: string;
  onContractTypeChange: (contractTypeId: string) => void;
  contractTypes: ContractType[];
  onClearFilters: () => void;
  hideContractTypeFilter?: boolean;
}

export function GuidelinesFilters({
  searchTerm,
  onSearchChange,
  levelFilter,
  onLevelFilterChange,
  contractTypeId,
  onContractTypeChange,
  contractTypes,
  onClearFilters,
  hideContractTypeFilter = false,
}: GuidelinesFiltersProps) {
  const { t } = useTranslation();
  const [localSearchTerm, setLocalSearchTerm] = useState(searchTerm);

  const impactLevels = [
    { value: 'all', label: t('guidelines.filters.level.all') },
    { value: 'high', label: t('guidelines.filters.level.high') },
    { value: 'medium', label: t('guidelines.filters.level.medium') },
    { value: 'low', label: t('guidelines.filters.level.low') },
  ];

  // Update local search term when prop changes
  useEffect(() => {
    setLocalSearchTerm(searchTerm);
  }, [searchTerm]);

  // Handle search input change with debouncing
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      onSearchChange(localSearchTerm);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [localSearchTerm, onSearchChange]);

  const handleSearchChange = (value: string) => {
    setLocalSearchTerm(value);
  };

  // Clear search input
  const clearSearch = () => {
    setLocalSearchTerm('');
    onSearchChange('');
  };

  // Check if any filters are active
  const hasActiveFilters = searchTerm || (levelFilter && levelFilter !== 'all');

  // Get active filter count for display
  const getActiveFilterCount = () => {
    let count = 0;
    if (searchTerm) count++;
    if (levelFilter && levelFilter !== 'all') count++;
    return count;
  };

  const activeFilterCount = getActiveFilterCount();

  return (
    <div className="space-y-4">
      {/* Contract Type Selection - only show if not hidden */}
      {!hideContractTypeFilter && (
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <Select
              value={contractTypeId || ""}
              onValueChange={onContractTypeChange}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder={t('guidelines.filters.contractType.placeholder')} />
              </SelectTrigger>
              <SelectContent>
                {contractTypes.map((contractType) => (
                  <SelectItem
                    key={contractType.contractTypeId}
                    value={contractType.contractTypeId}
                  >
                    <div className="flex flex-col">
                      <span className="font-medium">{contractType.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {contractType.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Search and Filters - only show when contract type is selected or when contract type filter is hidden */}
      {(contractTypeId || hideContractTypeFilter) && (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-1 flex-col gap-2 md:flex-row md:items-center">
            {/* Search Input */}
            <div className="relative flex-1 md:max-w-sm">
              <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder={t('guidelines.filters.search.placeholder')}
                value={localSearchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-9 pr-9"
              />
              {localSearchTerm && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearSearch}
                  className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0 hover:bg-muted"
                >
                  <XIcon className="h-4 w-4" />
                </Button>
              )}
            </div>

            {/* Level Filter */}
            <Select
              value={levelFilter || 'all'}
              onValueChange={onLevelFilterChange}
            >
              <SelectTrigger className="md:w-48">
                <div className="flex items-center gap-2">
                  <FilterIcon className="h-4 w-4" />
                  <SelectValue />
                </div>
              </SelectTrigger>
              <SelectContent>
                {impactLevels.map((level) => (
                  <SelectItem key={level.value} value={level.value}>
                    <div className="flex items-center gap-2">
                      <span>{level.label}</span>
                      {level.value !== 'all' && (
                        <Badge
                          variant="secondary"
                          className={`text-xs ${IMPACT_COLORS[level.value as ImpactLevel]}`}
                        >
                          {level.value}
                        </Badge>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Filter Actions */}
          <div className="flex items-center gap-2">
            {/* Active Filters Indicator */}
            {activeFilterCount > 0 && (
              <Badge variant="secondary" className="text-xs">
                {t('guidelines.filters.filterCount', { count: activeFilterCount })}
              </Badge>
            )}

            {/* Clear Filters Button */}
            {hasActiveFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={onClearFilters}
                className="text-xs"
              >
                <RefreshCcwIcon className="mr-1 h-3 w-3" />
                {t('guidelines.filters.clearFilters')}
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Active Filters Display */}
      {(contractTypeId || hideContractTypeFilter) && hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">{t('guidelines.filters.activeFilters')}</span>

          {searchTerm && (
            <Badge variant="outline" className="gap-1">
              {t('guidelines.filters.searchFilter', { term: searchTerm })}
              <Button
                variant="ghost"
                size="sm"
                onClick={clearSearch}
                className="h-4 w-4 p-0 hover:bg-transparent"
              >
                <XIcon className="h-3 w-3" />
              </Button>
            </Badge>
          )}

          {levelFilter && levelFilter !== 'all' && (
            <Badge variant="outline" className="gap-1">
              {t('guidelines.filters.levelFilter', { level: levelFilter })}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onLevelFilterChange('all')}
                className="h-4 w-4 p-0 hover:bg-transparent"
              >
                <XIcon className="h-3 w-3" />
              </Button>
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}

