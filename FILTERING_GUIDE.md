# Advanced Filtering Guide

## Overview

The filtering system provides powerful query capabilities for all models that inherit from `BaseService`. It supports:

- Multiple filter conditions with logical operators (AND/OR)
- Complex nested condition groups
- Various comparison operators (eq, ne, gt, contains, icontains, etc.)
- Sorting and ordering
- Pagination with metadata
- Type-safe validation with Pydantic

## Quick Start

### Basic Filter Example

```python
from app.services.filters import QueryFilter, Condition, FilterOperator

# Filter users with Gmail accounts
filters = QueryFilter(
    conditions=[
        Condition(field="email", operator=FilterOperator.ICONTAINS, value="gmail")
    ]
)

users = user_service.filter(session, filters)
```

### Filter with Pagination

```python
# Get first 10 active users, ordered by creation date
filters = QueryFilter(
    conditions=[
        Condition(field="is_active", operator=FilterOperator.EQ, value=True)
    ],
    order_by="created_at",
    order_direction="desc",
    limit=10,
    offset=0
)

result = user_service.filter_paginated(session, filters)
# Returns: {data: [...], total: 150, limit: 10, offset: 0, has_more: True}
```

## Available Operators

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal to | `id == 5` |
| `ne` | Not equal to | `status != "inactive"` |
| `gt` | Greater than | `age > 18` |
| `gte` | Greater than or equal | `score >= 100` |
| `lt` | Less than | `price < 50` |
| `lte` | Less than or equal | `quantity <= 10` |

### String Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `contains` | Contains substring (case-sensitive) | `name contains "John"` |
| `icontains` | Contains substring (case-insensitive) | `email icontains "gmail"` |
| `startswith` | Starts with | `username startswith "admin"` |
| `endswith` | Ends with | `email endswith ".com"` |

### List Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `in` | Value in list | `status in ["active", "pending"]` |
| `not_in` | Value not in list | `role not_in ["guest", "banned"]` |

### Null Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `is_null` | Field is NULL | `deleted_at is_null` |
| `is_not_null` | Field is NOT NULL | `phone is_not_null` |

## API Endpoints

### POST /users/filter

Filter users with advanced query options.

**Request Body:**

```json
{
    "conditions": [
        {
            "field": "email",
            "operator": "icontains",
            "value": "gmail"
        },
        {
            "field": "is_active",
            "operator": "eq",
            "value": true
        }
    ],
    "operator": "and",
    "order_by": "created_at",
    "order_direction": "desc",
    "limit": 10,
    "offset": 0
}
```

**Response:**

```json
[
    {
        "id": 1,
        "email": "user@gmail.com",
        "name": "John Doe",
        "is_active": true,
        "created_at": "2024-01-15T10:30:00"
    }
]
```

### POST /users/filter/paginated

Filter users with pagination metadata.

**Response:**

```json
{
    "data": [...],
    "total": 150,
    "limit": 10,
    "offset": 0,
    "has_more": true
}
```

## Complex Examples

### Multiple Conditions with AND

Find all active Gmail users created in the last month:

```json
{
    "conditions": [
        {
            "field": "email",
            "operator": "icontains",
            "value": "gmail"
        },
        {
            "field": "is_active",
            "operator": "eq",
            "value": true
        },
        {
            "field": "created_at",
            "operator": "gte",
            "value": "2024-01-01T00:00:00"
        }
    ],
    "operator": "and",
    "order_by": "created_at",
    "order_direction": "desc"
}
```

### Multiple Conditions with OR

Find users with Gmail OR Yahoo email:

```json
{
    "conditions": [
        {
            "field": "email",
            "operator": "icontains",
            "value": "gmail"
        },
        {
            "field": "email",
            "operator": "icontains",
            "value": "yahoo"
        }
    ],
    "operator": "or"
}
```

### Using IN Operator

Find users with specific providers:

```json
{
    "conditions": [
        {
            "field": "provider",
            "operator": "in",
            "value": ["google", "github", "microsoft"]
        }
    ]
}
```

### Null Check

Find users without a profile picture:

```json
{
    "conditions": [
        {
            "field": "picture",
            "operator": "is_null",
            "value": null
        }
    ]
}
```

### Nested Condition Groups

Complex query: Active users with (Gmail OR Yahoo) AND created this year:

```json
{
    "conditions": [
        {
            "field": "is_active",
            "operator": "eq",
            "value": true
        },
        {
            "conditions": [
                {
                    "field": "email",
                    "operator": "icontains",
                    "value": "gmail"
                },
                {
                    "field": "email",
                    "operator": "icontains",
                    "value": "yahoo"
                }
            ],
            "operator": "or"
        },
        {
            "field": "created_at",
            "operator": "gte",
            "value": "2024-01-01T00:00:00"
        }
    ],
    "operator": "and"
}
```

## Python Usage

### In Your Service

```python
from app.services.filters import QueryFilter, Condition, FilterOperator

# Simple filter
filters = QueryFilter(
    conditions=[
        Condition(field="is_active", operator=FilterOperator.EQ, value=True)
    ],
    limit=50
)

users = user_service.filter(session, filters)
```

### With Pagination Metadata

```python
result = user_service.filter_paginated(session, filters)

print(f"Found {result['total']} users")
print(f"Showing {len(result['data'])} users")
print(f"Has more: {result['has_more']}")
```

### Count Only (No Data)

```python
count = user_service.count_filtered(session, filters)
print(f"Total matching users: {count}")
```

## Adding Filtering to Your Own Models

If you're using `BaseService`, filtering is already available! No additional code needed.

```python
# Your service automatically inherits filtering
class PostService(BaseService[Post, PostCreate, PostUpdate, PostRead]):
    def __init__(self):
        super().__init__(
            model=Post,
            channel=posts_channel,
            read_schema=PostRead
        )

# Now you can filter posts!
post_service = PostService()

filters = QueryFilter(
    conditions=[
        Condition(field="user_id", operator=FilterOperator.EQ, value=123),
        Condition(field="title", operator=FilterOperator.ICONTAINS, value="python")
    ],
    order_by="created_at",
    order_direction="desc",
    limit=20
)

posts = post_service.filter(session, filters)
```

## Frontend Integration

### JavaScript/TypeScript Example

```typescript
async function filterUsers() {
    const response = await fetch('http://localhost:8000/users/filter/paginated', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            conditions: [
                {
                    field: 'email',
                    operator: 'icontains',
                    value: 'gmail'
                },
                {
                    field: 'is_active',
                    operator: 'eq',
                    value: true
                }
            ],
            operator: 'and',
            order_by: 'created_at',
            order_direction: 'desc',
            limit: 20,
            offset: 0
        })
    });

    const result = await response.json();
    console.log(`Found ${result.total} users`);
    console.log('Users:', result.data);
}
```

### React Hook Example

```typescript
import { useState } from 'react';

interface FilterParams {
    conditions: Array<{
        field: string;
        operator: string;
        value: any;
    }>;
    operator: 'and' | 'or';
    order_by?: string;
    order_direction?: 'asc' | 'desc';
    limit?: number;
    offset?: number;
}

function useUserFilter() {
    const [users, setUsers] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);

    const filterUsers = async (params: FilterParams) => {
        setLoading(true);
        try {
            const response = await fetch('/users/filter/paginated', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            const result = await response.json();
            setUsers(result.data);
            setTotal(result.total);
        } finally {
            setLoading(false);
        }
    };

    return { users, total, loading, filterUsers };
}

// Usage in component
function UserList() {
    const { users, total, loading, filterUsers } = useUserFilter();

    const handleSearch = () => {
        filterUsers({
            conditions: [
                { field: 'email', operator: 'icontains', value: 'gmail' }
            ],
            operator: 'and',
            limit: 20,
            offset: 0
        });
    };

    return (
        <div>
            <button onClick={handleSearch}>Search Gmail Users</button>
            {loading ? <p>Loading...</p> : (
                <>
                    <p>Total: {total}</p>
                    <ul>
                        {users.map(user => <li key={user.id}>{user.email}</li>)}
                    </ul>
                </>
            )}
        </div>
    );
}
```

## Performance Considerations

1. **Use indexes**: Ensure filtered fields have database indexes
2. **Limit results**: Always use `limit` to prevent large result sets
3. **Pagination**: Use `offset` and `limit` for pagination instead of fetching all data
4. **Selective filtering**: Only fetch fields you need
5. **Avoid complex nested groups**: Too many nested conditions can slow queries

## Validation

The filtering system includes automatic validation:

- **Field names**: Must be non-empty strings
- **Operators**: Must be valid FilterOperator enum values
- **Limit**: Between 1 and 1000 (default: 100)
- **Offset**: Must be >= 0 (default: 0)
- **Order direction**: Must be "asc" or "desc"

Invalid requests will return a 422 Unprocessable Entity error with details.

## Error Handling

### Invalid Field

If you filter by a field that doesn't exist on the model, the condition is silently skipped with a warning in logs:

```
WARNING - Campo 'invalid_field' no existe en User
```

### Invalid Operator

If you use an invalid operator, Pydantic validation will reject the request:

```json
{
    "detail": [
        {
            "loc": ["body", "conditions", 0, "operator"],
            "msg": "value is not a valid enumeration member",
            "type": "type_error.enum"
        }
    ]
}
```

## Best Practices

1. **Start simple**: Begin with basic filters and add complexity as needed
2. **Test your filters**: Verify filters return expected results
3. **Use pagination**: Always paginate large result sets
4. **Index filtered fields**: Add database indexes for frequently filtered fields
5. **Document your filters**: Document filter options for your API consumers
6. **Validate user input**: Sanitize and validate filter values from users
7. **Set reasonable limits**: Don't allow unlimited result sets

## Architecture

### Components

```
FilterMixin (provides filter methods)
    ↓
BaseService (inherits FilterMixin)
    ↓
UserService, PostService, etc. (inherit filtering automatically)
```

### Flow

```
1. Client sends filter request
2. Pydantic validates QueryFilter
3. QueryBuilder constructs SQL query
4. Session executes query
5. Results returned to client
```

## Testing

### Example Test

```python
def test_filter_users():
    # Create test users
    user1 = User(email="test@gmail.com", is_active=True)
    user2 = User(email="test@yahoo.com", is_active=True)
    user3 = User(email="test@hotmail.com", is_active=False)
    session.add_all([user1, user2, user3])
    session.commit()

    # Filter for active Gmail users
    filters = QueryFilter(
        conditions=[
            Condition(field="email", operator=FilterOperator.ICONTAINS, value="gmail"),
            Condition(field="is_active", operator=FilterOperator.EQ, value=True)
        ],
        operator=LogicalOperator.AND
    )

    results = user_service.filter(session, filters)

    assert len(results) == 1
    assert results[0].email == "test@gmail.com"
```

## Conclusion

The filtering system provides a powerful, type-safe, and flexible way to query your data. It integrates seamlessly with `BaseService`, requires no additional code per model, and supports complex queries with nested conditions.

For more examples, see:
- [BASE_SERVICE_ARCHITECTURE.md](BASE_SERVICE_ARCHITECTURE.md) - BaseService documentation
- [EXAMPLE_POST_MODEL.md](EXAMPLE_POST_MODEL.md) - Adding new models
- OpenAPI docs at http://localhost:8000/docs when server is running
