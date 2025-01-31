# Code Expert Rules Configuration Format

## Overview

The rules configuration file is a JSON document that defines languages, categories, and individual rules for code
evaluation. It uses a hierarchical structure where languages and categories are defined first, and then referenced by
individual rules.

## Structure

The JSON document contains three main sections:

- `languages`: Defines supported programming languages and their file patterns
- `categories`: Defines rule categories and their associated languages
- `rules`: Defines individual evaluation rules

```json
{
  "languages": [
    ...
  ],
  "categories": [
    ...
  ],
  "rules": [
    ...
  ]
}
```

## Languages Section

The `languages` section is an array of language definitions. Each language defines default patterns for identifying
relevant files. A language's rules apply to a repository if any file matches the **defaultPatterns**.

```json
{
  "languages": [
    {
      "name": "java",
      "defaultPatterns": [
        "**/*.java"
      ],
      "defaultExcludePatterns": [
        "**/test/**"
      ]
    }
  ]
}
```

### Language Properties

| Property                 | Type     | Required | Description                                      |
|--------------------------|----------|----------|--------------------------------------------------|
| `name`                   | string   | Yes      | The name of the programming language             |
| `defaultPatterns`        | string[] | Yes      | Glob patterns to identify files of this language |
| `defaultExcludePatterns` | string[] | No       | Glob patterns to exclude files from evaluation   |

## Categories Section

The `categories` section defines groups of related rules. Categories are associated with specific languages and can
define their own patterns. A category's rules apply to a repository when any of its associated languages are present
and, if the category specifies **exists** patterns, all of those pattern requirements are matched by files in the
repository.

```json
{
  "categories": [
    {
      "name": "Spring",
      "languages": [
        "java"
      ],
      "exists": [
        "**/pom.xml"
      ],
      "defaultPatterns": [
        "**/*Controller.java"
      ],
      "defaultExcludePatterns": [
        "**/test/**"
      ]
    }
  ]
}
```

### Category Properties

| Property                 | Type     | Required | Description                                              |
|--------------------------|----------|----------|----------------------------------------------------------|
| `name`                   | string   | Yes      | The name of the category                                 |
| `languages`              | string[] | Yes      | Names of languages this category applies to              |
| `exists`                 | string[] | No       | Glob patterns that must exist for this category to apply |
| `defaultPatterns`        | string[] | No       | Default glob patterns for rules in this category         |
| `defaultExcludePatterns` | string[] | No       | Default exclusion patterns for rules in this category    |

## Rules Section

The `rules` section defines individual evaluation rules. Each rule references a language and category, and can override
patterns.

```json
{
  "rules": [
    {
      "rule": "JAVA001",
      "ruleDesc": "Controllers should use constructor injection instead of field injection",
      "category": "Spring",
      "language": "java",
      "patterns": [
        "**/*Controller.java"
      ],
      "contextPatterns": [
        "**/application.yml",
        "**/application.properties"
      ],
      "excludePatterns": [
        "**/test/**"
      ]
    }
  ]
}
```

### Rule Properties

| Property          | Type     | Required | Description                                        |
|-------------------|----------|----------|----------------------------------------------------|
| `rule`            | string   | Yes      | Unique identifier for the rule                     |
| `ruleDesc`        | string   | Yes      | Description of what the rule evaluates             |
| `category`        | string   | Yes      | Name of the category this rule belongs to          |
| `language`        | string   | Yes      | Name of the language this rule applies to          |
| `patterns`        | string[] | No       | Glob patterns to identify files to evaluate        |
| `contextPatterns` | string[] | No       | Glob patterns to identify files needed for context |
| `excludePatterns` | string[] | No       | Glob patterns to exclude files from evaluation     |

## Pattern Resolution

When evaluating which files to check for a rule, the system uses patterns in the following order:

1. Rule-specific patterns (`patterns`)
2. Category default patterns (`defaultPatterns`)
3. Language default patterns (`defaultPatterns`)

The same hierarchy applies for exclude patterns.

## Complete Example

```json
{
  "languages": [
    {
      "name": "java",
      "defaultPatterns": [
        "**/*.java"
      ],
      "defaultExcludePatterns": [
        "**/test/**"
      ]
    }
  ],
  "categories": [
    {
      "name": "Spring",
      "languages": [
        "java"
      ],
      "exists": [
        "**/pom.xml"
      ],
      "defaultPatterns": [
        "**/*Controller.java"
      ],
      "defaultExcludePatterns": [
        "**/test/**"
      ]
    },
    {
      "name": "Security",
      "languages": [
        "java"
      ],
      "defaultPatterns": [
        "**/*.java"
      ]
    }
  ],
  "rules": [
    {
      "rule": "JAVA001",
      "ruleDesc": "Controllers should use constructor injection instead of field injection",
      "category": "Spring",
      "language": "java",
      "patterns": [
        "**/*Controller.java"
      ]
    },
    {
      "rule": "SEC001",
      "ruleDesc": "Avoid using System.exit()",
      "category": "Security",
      "language": "java",
      "contextPatterns": [
        "**/pom.xml"
      ]
    }
  ]
}
```

## Notes

1. All glob patterns are evaluated by Python [fnmatch](https://docs.python.org/3/library/fnmatch.html)
2. Context patterns are only needed for rules that require additional files for evaluation
3. The `exists` patterns in categories help determine if a category applies to a repository
4. Rule IDs (`rule` property) can be either strings or numbers but will be converted to strings internally
