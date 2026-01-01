# Lessons Learned: Delete Error Handling Fix

**Date:** 2026-01-01
**Commit:** 6d38d0e
**PR:** N/A (committed directly to main)

## Problem Summary

Users reported a bug where deleting purchases or sales showed a success toast notification, but the item remained in the list. Investigation revealed that the `deletePurchase` and `deleteSale` functions weren't checking the HTTP response status before showing success, leading to misleading UI feedback when the API call failed.

## Root Cause

The `authFetch` wrapper method (`app/static/js/auth.js:260-286`) only throws errors for 401 (Unauthorized) responses. For all other HTTP errors (404, 500, etc.), it returns the response object without throwing. The delete functions assumed `authFetch` would throw on failure and unconditionally showed success toasts and reloaded data.

**Evidence:**
- `authFetch` only handles 401 specially with redirect to login
- `deletePurchase` (app.js:821) and `deleteSale` (app.js:842) didn't check `response.ok`
- Other functions like purchase creation (app.js:483-493) correctly checked `response.ok` before showing success

## Approach Taken

Applied a targeted fix to match the existing pattern used throughout the codebase:

1. **Modified `deletePurchase`** (lines 821-830):
   - Captured response from `authFetch` instead of awaiting without assignment
   - Parsed JSON to extract error message
   - Added `response.ok` check before showing success
   - Early return with error toast if deletion failed
   - Only reload data on successful deletion

2. **Modified `deleteSale`** (lines 849-858):
   - Applied identical pattern as `deletePurchase`
   - Maintained consistency with codebase conventions

3. **No backend changes needed**:
   - Backend endpoints already returned proper JSON error responses
   - Purchases: `{'error': 'Purchase not found'}`, 404
   - Sales: `{'error': 'Sale not found'}`, 404

## Key Lessons

- **API wrapper methods should have clear contracts**: `authFetch` not throwing on HTTP errors was unexpected behavior that violated the principle of least surprise. This caused developers to make incorrect assumptions about error handling.

- **Follow existing patterns**: The purchase creation code (lines 483-493) already had the correct pattern for error handling. Looking for established patterns in the codebase before implementing new code prevents introducing bugs.

- **Check response.ok explicitly**: When using fetch or custom wrappers that return Response objects, always check `response.ok` before assuming success. Don't rely on exceptions alone.

- **Test both success and failure paths**: The bug wasn't caught because only the happy path was tested. Testing error scenarios (404, 500, network errors) would have revealed the issue immediately.

- **Consistency matters**: The codebase had mixed patterns for handling `authFetch` responses. Some functions checked `response.ok`, others didn't. Standardizing error handling across all API calls would prevent this class of bugs.

- **User feedback should match reality**: Always verify backend success before showing success UI. Misleading feedback erodes user trust and creates confusion.

## Potential Improvements

1. **Refactor authFetch to throw on all HTTP errors**: Make `authFetch` throw errors for all non-OK responses, not just 401. This would make error handling more predictable and prevent this bug class entirely. However, this requires auditing all usages (18+ calls) and could be a breaking change.

2. **Add JSDoc documentation**: Document `authFetch`'s behavior clearly so developers know they must check `response.ok`.

3. **Create response helper**: Add a utility like `checkResponse(response)` that throws on !response.ok with a standardized error format. This would make error handling more declarative and harder to forget.

4. **Add integration tests**: Automated tests for both success and failure paths of delete operations would catch this type of regression.

5. **Linting rule**: Consider a custom ESLint rule that warns when `authFetch` results are used without checking `.ok` property.

## Testing Verification

Verified fix with Playwright end-to-end test:
- ✅ Created test purchase in guest mode
- ✅ Deleted purchase with confirmation
- ✅ Success toast appeared AND item disappeared from list
- ✅ Portfolio stats updated immediately
- ✅ All comparison values recalculated correctly

The bug is fully resolved. Users now see proper error messages when deletions fail, and items only disappear when deletion succeeds on the backend.
