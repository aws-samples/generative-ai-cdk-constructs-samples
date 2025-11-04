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

import { faker } from "@faker-js/faker";

/**
 * Configure faker for deterministic mock data generation
 */
export function setupFaker(): void {
  // Use fixed seed for consistent results across runs
  faker.seed(12345);

  // Faker defaults to English locale
}

/**
 * Contract-specific faker utilities
 */
export const mockFaker = {
  /**
   * Generate realistic contract clause text
   */
  clauseText: (): string => {
    const clauseTemplates = [
      "The Party shall be responsible for %s as outlined in this agreement.",
      "In accordance with applicable regulations, %s must be maintained at all times.",
      "This contract governs %s between the contracting parties.",
      "The obligations regarding %s are defined in the following terms.",
      "Payment terms for %s shall be executed within the specified timeframe.",
      "Liability concerning %s is limited to the scope defined herein.",
      "Confidentiality of %s must be preserved throughout the contract duration.",
    ];

    const subjects = [
      "service delivery standards",
      "data protection requirements",
      "intellectual property rights",
      "quality assurance measures",
      "compliance monitoring procedures",
      "risk management protocols",
      "performance metrics",
    ];

    const template = faker.helpers.arrayElement(clauseTemplates);
    const subject = faker.helpers.arrayElement(subjects);
    return template.replace("%s", subject);
  },

  /**
   * Generate clause type information
   */
  clauseType: (): { typeId: string; typeName: string } => {
    const types = [
      { typeId: "payment-terms", typeName: "Payment Terms" },
      { typeId: "liability-clause", typeName: "Liability Limitation" },
      { typeId: "confidentiality", typeName: "Confidentiality Agreement" },
      { typeId: "service-level", typeName: "Service Level Agreement" },
      { typeId: "termination", typeName: "Contract Termination" },
      {
        typeId: "intellectual-property",
        typeName: "Intellectual Property Rights",
      },
      { typeId: "compliance", typeName: "Regulatory Compliance" },
    ];

    return faker.helpers.arrayElement(types);
  },

  /**
   * Generate compliance analysis text
   */
  complianceAnalysis: (isCompliant: boolean): string => {
    if (isCompliant) {
      return faker.helpers.arrayElement([
        "This clause meets all regulatory requirements and follows industry best practices.",
        "The language used is clear, compliant, and legally sound.",
        "All necessary elements are present and properly structured.",
        "This provision aligns with applicable laws and regulations.",
      ]);
    } else {
      return faker.helpers.arrayElement([
        "This clause lacks specific requirements mandated by current regulations.",
        "The language used may create ambiguity and potential legal risks.",
        "Missing key provisions that are required for full compliance.",
        "This section needs revision to meet industry standards.",
      ]);
    }
  },
};

// Initialize faker on import
setupFaker();
