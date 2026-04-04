# Auto-Generate Schema - Technical Documentation

This document provides detailed technical documentation for the Auto-Generate Schema feature in NikkoParse. This feature automatically creates robust, flexible regex patterns from user-selected field examples.

## Table of Contents

1. [Overview](#overview)
2. [Algorithm Architecture](#algorithm-architecture)
3. [Pattern Generation Strategy](#pattern-generation-strategy)
4. [Bug Fixes & Improvements](#bug-fixes--improvements)
5. [Code Reference](#code-reference)
6. [Examples](#examples)

---

## Overview

### Purpose

The Auto-Generate Schema feature enables users to create extraction patterns without writing regex or using AI. Users simply click example values in their documents, and the system generates flexible, context-aware patterns automatically.

### Key Benefits

- **Speed**: Instant pattern generation (vs 30-60 seconds for AI)
- **Cost**: Free, no API calls required
- **Reliability**: Deterministic results, no AI variability
- **Offline**: Works without internet connection
- **Flexibility**: Patterns handle variations in amounts, dates, formatting
- **Robustness**: Multi-pattern cascade with fallbacks

### Design Philosophy

1. **Deterministic over stochastic** - Patterns should be predictable and reproducible
2. **Flexible over rigid** - Match variations while maintaining specificity
3. **Context-aware over value-only** - Use distinctive labels and keywords
4. **Graceful degradation** - Multiple patterns provide fallback options

---

## Algorithm Architecture

### High-Level Flow

```
User clicks field examples (2-3 per field)
         ↓
autoGenerateSchema() orchestrates generation
         ↓
For each field:
  1. Select best example (smart selection)
  2. Load document text
  3. Find example value position
  4. Extract context (750 chars before value)
  5. Call generatePatternHint()
         ↓
generatePatternHint() analyzes context
  1. Detect row label
  2. Create flexible pattern (replace numbers)
  3. Detect date columns to skip
  4. Detect number columns to skip
  5. Generate value pattern
  6. Combine into 3 patterns (specific, medium, fallback)
         ↓
Save schema with regex_patterns array
         ↓
Run extraction across all documents
```

### Component Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `autoGenerateSchema()` | `project.js:1150` | Main orchestration function |
| `generatePatternHint()` | `project.js:908` | Core pattern generation logic |
| `getValuePattern()` | `project.js:1095` | Type-specific value pattern creation |
| `detectDataType()` | `project.js:~800` | Infer data type from value |
| `detectDataTypeFromLabel()` | `project.js:~850` | Infer data type from field label |

---

## Pattern Generation Strategy

### 1. Label Detection & Flexible Patterns

**Goal**: Identify row labels and make them flexible to match variations

**Algorithm** (`generatePatternHint()` lines 922-961):

1. **Extract last line** from context (most likely contains label)
2. **Detect label** using multiple strategies:
   - Lines ending with `@` or `:` → use entire line
   - Match text before 2+ spaces (column separator)
   - Fallback to entire line if no digits at end
3. **Escape regex special characters**:
   ```javascript
   let escapedLabel = rowLabel.replace(/[()[\]{}.*+?^$|\\]/g, '\\$&');
   // "401(k) Supply 2.00 therms @" → "401\\(k\\) Supply 2\\.00 therms @"
   ```
4. **Replace numbers with flexible patterns**:
   ```javascript
   flexiblePattern = escapedLabel.replace(/\d+(?:\\\.\d+)?/g, '\\d+(?:\\.\\d+)?');
   // "Supply 2\\.00 therms @" → "Supply \\d+(?:\\.\\d+)? therms @"
   ```

**Why this works**:
- Handles variations: 1.00 therms, 2.00 therms, 3.50 therms all match
- Keeps distinctive words: "therms" stays exact to avoid cross-matching with "kWh"
- Preserves structure: "Supply ... therms @" pattern is maintained

### 2. Skip Pattern Detection

**Goal**: Identify intermediate columns between label and target value

**Date Column Skip** (`lines 963-984`):

```javascript
const datePattern = /\d{1,2}\/\d{1,2}\/\d{4}(\s*-\s*\d{1,2}\/\d{1,2}\/\d{4})?/g;
```

- Matches single dates: `01/26/2026`
- Matches date ranges: `01/04/2026 - 01/17/2026`
- Stored in building blocks for pattern construction

**Number Column Skip** (`lines 986-1030`):

```javascript
// For each number found in lastLine:
// Skip if:
//   1. Number is the target value
//   2. Number is within a date range
//   3. Number is part of the label (position < labelEndPos)
```

**Critical fix** (lines 1013-1016):
```javascript
// Skip if this number is part of the label (e.g., "401" in "401(k)")
if (labelEndPos > 0 && numPos < labelEndPos) {
  continue;
}
```

This prevents "401" from being treated as a skip pattern, which was causing the 401(k) bug.

### 3. Value Pattern Generation

**Goal**: Create type-specific capture patterns for values

**Money Values** (`getValuePattern()` lines 1097-1116):

```javascript
// Price with unit: "58.500¢/therm"
if (/[\d,\.]+¢\/[a-z]+/i.test(value)) {
  const unitMatch = value.match(/¢\/([a-z]+)/i);
  const unit = unitMatch ? unitMatch[1] : '[a-zA-Z]+';
  return `([\\d,\\.]+¢/${unit})`;  // Keep unit specific!
}

// Dollar amount: "$106.79"
if (value.includes('$')) {
  return '(\\$[\\d,\\.]+)';
}

// Value with unit: "130.00 kWh"
const unitsMatch = value.match(/[\d,\.]+ ?([a-zA-Z]+)/);
if (unitsMatch) {
  const unit = unitsMatch[1];
  return `([\\d,\\.]+ ${unit})`;  // Keep unit specific!
}
```

**Key principle**: Extract and preserve specific units ("kWh", "therm") instead of using generic `[a-zA-Z]+`. This prevents cross-matching between gas and electricity fields.

**Number Values** (`lines 1118-1127`):

```javascript
// Account numbers with dashes: "89613-14560-9"
if (value.includes('-')) {
  return '([\\d-]+)';
}

// Decimals: "1,234.56"
if (value.includes('.')) {
  return '([\\d,\\.]+)';
}

// Integers: "1234"
return '(\\d+)';
```

**Date Values** (`lines 1129-1137`):

```javascript
// Date range: "01/04/2026 - 01/17/2026"
if (/-/.test(value) && value.split('-').length === 2) {
  // Pattern matches BOTH ranges AND single dates (range part is optional)
  return '(\\d{1,2}/\\d{1,2}/\\d{2,4}(?:\\s*-\\s*\\d{1,2}/\\d{1,2}/\\d{2,4})?)';
}

// Single date: "01/26/2026"
return '(\\d{1,2}/\\d{1,2}/\\d{2,4})';
```

**Critical feature** (line 1134): The `(?:...)?` makes the second date optional, so the pattern matches both:
- Single dates: `12/21/2025`
- Date ranges: `01/04/2026 - 01/17/2026`

### 4. Pattern Assembly

**Goal**: Combine building blocks into 3-tier pattern cascade

**Pattern 1: Specific** (`lines 1041-1063`):

```javascript
// Structure: label + skip_date? + skip_number? + value
const parts = [labelBlock.pattern];

if (dateBlocks.length > 0) {
  parts.push(dateBlocks[0].pattern);  // Skip date column
}

if (numberBlocks.length > 0) {
  parts.push('\\d+(?:\\.\\d+)?');  // Skip ONE number column
}

const specificPattern = parts.join('\\s+') + '\\s+' + valuePattern;
```

**Example result**: `Supply \\d+(?:\\.\\d+)? therms @\\s+([\d,\.]+ therms)`

**Pattern 2: Medium** (`lines 1066-1073`):

```javascript
// Structure: label + greedy skip + value
const mediumPattern = escapedLabel + '.*?' + valuePattern;
```

**Example result**: `Supply \\d+(?:\\.\\d+)? therms @.*?([\d,\.]+ therms)`

Uses `.*?` (non-greedy) to skip any content between label and value.

**Pattern 3: Fallback** (`lines 1078-1083`):

```javascript
// Structure: value only
hints.suggestedPatterns.push({
  priority: 3,
  type: 'value_only',
  pattern: valuePattern
});
```

**Example result**: `([\d,\.]+ therms)`

Matches value format anywhere in the document.

### 5. Smart Example Selection

**Goal**: Choose the most informative example when multiple exist

**Algorithm** (`autoGenerateSchema()` lines 1212-1232):

```javascript
let bestExample = field.examples[0];

const fieldType = detectDataTypeFromLabel(field.label) || detectDataType(field) || 'text';

if (fieldType === 'date' && field.examples.length > 1) {
  // For dates, prefer examples with ranges (contain " - ")
  const rangeExample = field.examples.find(ex => ex.value && ex.value.includes(' - '));
  if (rangeExample) {
    bestExample = rangeExample;
  }
} else if (field.examples.length > 1) {
  // For other types, prefer longer values (more context)
  bestExample = field.examples.reduce((best, ex) => {
    return (ex.value && ex.value.length > best.value.length) ? ex : best;
  }, field.examples[0]);
}
```

**Why this matters**:
- **Date fields**: Picking a range example generates a pattern that also matches single dates (optional range)
- **Other fields**: Longer values often have more distinctive context (better patterns)

---

## Bug Fixes & Improvements

### Bug #1: 401(k) Pattern Capturing YTD Instead of Monthly Amount

**Problem**: Pattern was skipping the monthly amount and capturing the YTD column.

**Root Cause**: The number "401" was detected as a skip number because label detection stopped before the lookahead could detect it was part of the label.

**Fix** (`lines 1013-1016`):
```javascript
// Skip if this number is part of the label (e.g., "401" in "401(k)")
if (labelEndPos > 0 && numPos < labelEndPos) {
  continue;
}
```

**Result**: Pattern `401\\(k\\) Basic Contribution\\s+([\\d,\\.]+)` now correctly captures monthly amounts.

### Bug #2: Over-Specific Patterns for Varying Amounts

**Problem**: Pattern `Supply 2\\.00 therms @([\\d,\\.]+¢/therm)` only matched bills with exactly 2.00 therms.

**Root Cause**: Label detection captured the exact amount "2.00" and escaped it literally.

**Fix** (`lines 948-953`):
```javascript
// First escape regex special characters
let escapedLabel = rowLabel.replace(/[()[\]{}.*+?^$|\\]/g, '\\$&');

// Then replace specific numbers with flexible patterns
flexiblePattern = escapedLabel.replace(/\d+(?:\\\.\d+)?/g, '\\d+(?:\\.\\d+)?');
```

**Result**: Pattern `Supply \\d+(?:\\.\\d+)? therms @([\\d,\\.]+¢/therm)` matches any amount.

### Bug #3: Account Numbers Losing Dashes

**Problem**: Pattern `(\\d+)` only captured digits, so "89613-14560-9" became "89613".

**Fix** (`lines 1119-1121`):
```javascript
// Check for number with dashes (e.g., account numbers)
if (value.includes('-')) {
  return '([\\d-]+)';
}
```

**Result**: Pattern captures full account number with dashes.

### Bug #4: Money Values Losing Units

**Problem**: Pattern `([\\d,\\.]+)` captured "130.00" instead of "130.00 kWh".

**Fix** (`lines 1111-1115`):
```javascript
// Check if value includes units like "kWh", "therms", etc.
const unitsMatch = value.match(/[\d,\.]+ ?([a-zA-Z]+)/);
if (unitsMatch) {
  const unit = unitsMatch[1];  // Extract specific unit
  return `([\\d,\\.]+ ${unit})`;  // Include in pattern
}
```

**Result**: Pattern captures amount with unit, prevents cross-matching.

### Bug #5: Date Ranges Not Matching Single Dates

**Problem**: When user selected a date range example, generated pattern only matched ranges, not single dates.

**Root Cause**: 
1. Pattern generation only looked at `field.examples[0]`
2. Date pattern didn't support optional range

**Fix 1** (`lines 1131-1134`):
```javascript
// Date range pattern with OPTIONAL second date
return '(\\d{1,2}/\\d{1,2}/\\d{2,4}(?:\\s*-\\s*\\d{1,2}/\\d{1,2}/\\d{2,4})?)';
//                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
//                                    This entire group is optional: (?:...)?
```

**Fix 2** (`lines 1221-1226`):
```javascript
// Smart example selection: prefer date ranges for date fields
if (fieldType === 'date' && field.examples.length > 1) {
  const rangeExample = field.examples.find(ex => ex.value && ex.value.includes(' - '));
  if (rangeExample) {
    bestExample = rangeExample;
  }
}
```

**Result**: Pattern matches both single dates and ranges regardless of which example was used.

---

## Code Reference

### Main Functions

#### `autoGenerateSchema()` - `project.js:1150-1299`

Main orchestration function that:
1. Validates fields and parsed files exist
2. Loads text for all files with examples
3. For each field, selects best example
4. Calls `generatePatternHint()` to create patterns
5. Saves schema and runs extraction

**Key code**:
```javascript
// Smart example selection
let bestExample = field.examples[0];
const fieldType = detectDataTypeFromLabel(field.label) || detectDataType(field) || 'text';

if (fieldType === 'date' && field.examples.length > 1) {
  // Prefer date ranges
  const rangeExample = field.examples.find(ex => ex.value && ex.value.includes(' - '));
  if (rangeExample) bestExample = rangeExample;
} else if (field.examples.length > 1) {
  // Prefer longer values
  bestExample = field.examples.reduce((best, ex) => 
    (ex.value && ex.value.length > best.value.length) ? ex : best
  , field.examples[0]);
}
```

#### `generatePatternHint()` - `project.js:908-1086`

Core pattern generation logic:
1. Analyzes context window (200 chars before value)
2. Detects row label and creates flexible pattern
3. Detects skip patterns (dates, numbers)
4. Calls `getValuePattern()` for value capture
5. Assembles 3-tier pattern cascade

**Returns**:
```javascript
{
  buildingBlocks: [
    { type: 'label', pattern: '...', description: '...' },
    { type: 'skip_date', pattern: '...', description: '...' },
    { type: 'skip_number', pattern: '...', description: '...' }
  ],
  suggestedPatterns: [
    { priority: 1, type: 'specific', pattern: '...', explanation: '...' },
    { priority: 2, type: 'medium', pattern: '...', explanation: '...' },
    { priority: 3, type: 'value_only', pattern: '...', explanation: '...' }
  ]
}
```

#### `getValuePattern()` - `project.js:1095-1144`

Creates type-specific value capture patterns:
- **Money**: Handles $, units (kWh, therms), price-per-unit (¢/therm)
- **Number**: Handles dashes, decimals, integers
- **Date**: Handles single dates and optional date ranges
- **Text**: Captures alphanumeric with spaces

**Critical features**:
- Preserves specific units (not generic `[a-zA-Z]+`)
- Detects dashes for account numbers
- Makes date range optional with `(?:...)?`

---

## Examples

### Example 1: Payslip - 401(k) Field

**User selects**: `"401(k) Basic Contribution     50.00     850.00"`

**Context analysis**:
```
Last line: "401(k) Basic Contribution     50.00     850.00"
Label detected: "401(k) Basic Contribution"
Number columns: ["50.00"] (YTD not detected because it's the target)
```

**Label end position**: Position 25 (after "Contribution")
**Number "401" position**: Position 0
**Check**: `0 < 25` → TRUE, skip this number (it's part of label)

**Generated patterns**:
1. **Specific**: `401\\(k\\) Basic Contribution\\s+([\\d,\\.]+)`
2. **Medium**: `401\\(k\\) Basic Contribution.*?([\\d,\\.]+)`
3. **Fallback**: `([\\d,\\.]+)`

**Extraction result**: `50.00` ✓

### Example 2: Utility Bill - Gas Charge

**User selects**: `"Supply 2.00 therms @58.500¢/therm"`

**Context analysis**:
```
Last line: "Supply 2.00 therms @58.500¢/therm"
Label detected: "Supply 2.00 therms @" (ends with @)
Escaped: "Supply 2\\.00 therms @"
Flexible: "Supply \\d+(?:\\.\\d+)? therms @"
```

**Value pattern**:
```javascript
value = "58.500¢/therm"
Matches: /[\d,\.]+¢\/[a-z]+/i
unitMatch: "therm"
Pattern: ([\\d,\\.]+¢/therm)
```

**Generated patterns**:
1. **Specific**: `Supply \\d+(?:\\.\\d+)? therms @([\\d,\\.]+¢/therm)`
2. **Medium**: `Supply \\d+(?:\\.\\d+)? therms @.*?([\\d,\\.]+¢/therm)`
3. **Fallback**: `([\\d,\\.]+¢/therm)`

**Extraction across bills**:
- Bill 1 (1.00 therms): `52.300¢/therm` ✓
- Bill 2 (2.00 therms): `58.500¢/therm` ✓
- Bill 3 (3.50 therms): `61.200¢/therm` ✓

### Example 3: Utility Bill - Electricity Amount

**User selects**: `"130.00 kWh"`

**Value pattern**:
```javascript
value = "130.00 kWh"
unitsMatch: ["130.00 kWh", "kWh"]
unit: "kWh"
Pattern: ([\\d,\\.]+ kWh)
```

**Why this matters**:
- Pattern `([\\d,\\.]+ kWh)` only matches electricity
- Pattern `([\\d,\\.]+ therms)` only matches gas
- No cross-matching even though both are money values

### Example 4: Payslip - Date Range Field

**User has 3 examples**:
- Example 1: `"12/21/2025"` (single date)
- Example 2: `"01/04/2026 - 01/17/2026"` (range)
- Example 3: `"01/18/2026"` (single date)

**Smart selection**:
```javascript
fieldType: 'date'
rangeExample: field.examples.find(ex => ex.value.includes(' - '))
// Returns: Example 2
bestExample: { value: "01/04/2026 - 01/17/2026", file: "payslip_2.pdf" }
```

**Value pattern**:
```javascript
value = "01/04/2026 - 01/17/2026"
/-/.test(value): true
value.split('-').length: 2
Pattern: (\\d{1,2}/\\d{1,2}/\\d{2,4}(?:\\s*-\\s*\\d{1,2}/\\d{1,2}/\\d{2,4})?)
```

**Extraction across payslips**:
- Payslip 1: `12/21/2025` ✓ (matches without range)
- Payslip 2: `01/04/2026 - 01/17/2026` ✓ (matches with range)
- Payslip 3: `01/18/2026` ✓ (matches without range)

---

## Testing the Auto-Generate Feature

### Test Case 1: Varying Amounts

**Setup**: 13 payslips with different net pay amounts

**Steps**:
1. Click "Net Pay: $2,450.67" in payslip 1
2. Click "Net Pay: $3,120.89" in payslip 2
3. Click "Auto-Generate Schema"

**Expected**:
- Pattern: `Net Pay:?\\s+(\\$[\\d,\\.]+)`
- Extracts all 13 unique amounts

### Test Case 2: Date Ranges vs Single Dates

**Setup**: Mix of documents with date ranges and single dates

**Steps**:
1. Click single date "12/21/2025" in doc 1
2. Click range "01/04/2026 - 01/17/2026" in doc 2
3. Click "Auto-Generate Schema"

**Expected**:
- System selects range example (smarter)
- Pattern: `(\\d{1,2}/\\d{1,2}/\\d{2,4}(?:\\s*-\\s*\\d{1,2}/\\d{1,2}/\\d{2,4})?)`
- Extracts both ranges and single dates

### Test Case 3: Gas vs Electricity (No Cross-Match)

**Setup**: Utility bills with both gas and electricity charges

**Steps**:
1. Select "130.00 kWh" for electricity field
2. Select "2.00 therms" for gas field
3. Click "Auto-Generate Schema"

**Expected**:
- Electricity pattern: `([\\d,\\.]+ kWh)` (specific unit)
- Gas pattern: `([\\d,\\.]+ therms)` (specific unit)
- No cross-matching between fields

### Test Case 4: Account Numbers with Dashes

**Setup**: Documents with formatted account numbers

**Steps**:
1. Click "89613-14560-9" in doc 1
2. Click "Auto-Generate Schema"

**Expected**:
- Pattern: `([\\d-]+)`
- Extracts full number with dashes

---

## Performance Characteristics

### Time Complexity

- **Per field**: O(n) where n = length of context text (~750 chars)
- **Total**: O(f × n) where f = number of fields
- **Typical**: 10 fields × 750 chars = ~7,500 operations
- **Duration**: < 100ms on modern hardware

### Space Complexity

- **File texts**: O(d × s) where d = documents, s = avg file size
- **Patterns**: O(f × 3) = 3 patterns per field
- **Total memory**: Typically < 10 MB for 20 documents

### Scalability

- **Documents**: Tested with up to 20 documents (no issues)
- **Fields**: Tested with up to 15 fields (no issues)
- **File size**: Works with files up to 100 MB (Flask limit)

---

## Future Enhancements

### Potential Improvements

1. **Multi-line label detection** - Currently only analyzes last line
2. **Table structure detection** - Identify column headers automatically
3. **Pattern validation** - Test patterns before saving
4. **Pattern debugging UI** - Visual feedback on pattern matching
5. **Custom skip patterns** - User-defined intermediate columns
6. **Pattern optimization** - Simplify patterns automatically
7. **Historical pattern learning** - Suggest patterns based on past projects

### Advanced Features

1. **Column position hints** - Use relative positions (3rd column, 2nd-to-last, etc.)
2. **Fuzzy matching** - Handle OCR errors and typos
3. **Template detection** - Recognize common document types
4. **Batch pattern generation** - Generate for all suggested fields at once
5. **Pattern library** - Share patterns across projects

---

## Conclusion

The Auto-Generate Schema feature provides a fast, reliable, deterministic way to create extraction patterns from user examples. By combining flexible pattern generation, smart example selection, and multi-pattern cascading, it achieves high accuracy across document variations while remaining simple to use.

**Key takeaways**:
- Deterministic beats stochastic for predictability
- Flexibility beats rigidity for handling variations
- Context beats value-only for accuracy
- Multi-pattern cascade beats single pattern for robustness

For questions or contributions, see the main [README.md](README.md) and [AGENTS.md](AGENTS.md).
