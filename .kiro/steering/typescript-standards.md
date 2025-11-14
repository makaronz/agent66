---
inclusion: fileMatch
fileMatchPattern: '**/*.{ts,tsx}'
---

# TypeScript Standards & Guidelines for App_v2

## 🎯 TypeScript Configuration Standards

### Version Consistency
- **Always use TypeScript 5.3.3** across frontend and backend
- Maintain identical major/minor versions for consistency
- Update dependencies together to avoid compatibility issues

### Strict Configuration
```json
// tsconfig.json - Required settings
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

## 🏗️ Type Definition Patterns

### Interface Design
```typescript
// ✅ CORRECT: Comprehensive interface definitions
interface User {
  readonly id: string;
  name: string;
  email: string;
  role: UserRole;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  lastLogin?: Date;
}

type UserRole = 'user' | 'admin' | 'moderator';

// ✅ CORRECT: Generic API response type
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  pagination?: PaginationInfo;
}

interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// ❌ INCORRECT: Using any or loose typing
interface User {
  id: any;
  data: any;
  metadata?: any;
}
```

### Utility Types Usage
```typescript
// ✅ CORRECT: Leverage TypeScript utility types
type CreateUserRequest = Omit<User, 'id' | 'createdAt' | 'updatedAt'>;
type UpdateUserRequest = Partial<Pick<User, 'name' | 'email' | 'role'>>;
type UserPublicInfo = Pick<User, 'id' | 'name' | 'email'>;

// ✅ CORRECT: Custom utility types
type NonNullable<T> = T extends null | undefined ? never : T;
type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

// Usage
type UserWithRequiredEmail = RequiredFields<User, 'email'>;
```

## 🔒 Type Safety Patterns

### Runtime Type Validation
```typescript
// ✅ CORRECT: Type guards with Zod integration
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(2).max(100),
  email: z.string().email(),
  role: z.enum(['user', 'admin', 'moderator']),
  isActive: z.boolean().default(true),
});

type User = z.infer<typeof UserSchema>;

// Type guard function
function isUser(obj: unknown): obj is User {
  return UserSchema.safeParse(obj).success;
}

// Usage in API endpoints
app.post('/users', (req, res) => {
  const parseResult = UserSchema.safeParse(req.body);
  if (!parseResult.success) {
    return res.status(400).json({
      error: 'Invalid user data',
      details: parseResult.error.errors
    });
  }
  
  const userData: User = parseResult.data;
  // Type-safe from this point
});
```

### Discriminated Unions
```typescript
// ✅ CORRECT: Discriminated unions for state management
type LoadingState = {
  status: 'loading';
  progress?: number;
};

type SuccessState = {
  status: 'success';
  data: User[];
  timestamp: Date;
};

type ErrorState = {
  status: 'error';
  error: string;
  retryCount: number;
};

type AsyncState = LoadingState | SuccessState | ErrorState;

// Type-safe state handling
function handleState(state: AsyncState) {
  switch (state.status) {
    case 'loading':
      return `Loading... ${state.progress || 0}%`;
    case 'success':
      return `Loaded ${state.data.length} users at ${state.timestamp}`;
    case 'error':
      return `Error: ${state.error} (retry ${state.retryCount})`;
    default:
      // TypeScript ensures exhaustive checking
      const _exhaustive: never = state;
      return _exhaustive;
  }
}
```

## 🎣 React + TypeScript Patterns

### Component Props Typing
```typescript
// ✅ CORRECT: Comprehensive component typing
interface UserCardProps {
  user: User;
  onEdit?: (user: User) => void;
  onDelete?: (userId: string) => Promise<void>;
  className?: string;
  children?: React.ReactNode;
}

// ✅ CORRECT: Generic component props
interface ListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  keyExtractor: (item: T) => string;
  loading?: boolean;
  emptyMessage?: string;
}

function List<T>({ items, renderItem, keyExtractor, loading, emptyMessage }: ListProps<T>) {
  if (loading) return <div>Loading...</div>;
  if (items.length === 0) return <div>{emptyMessage || 'No items'}</div>;
  
  return (
    <ul>
      {items.map((item, index) => (
        <li key={keyExtractor(item)}>
          {renderItem(item, index)}
        </li>
      ))}
    </ul>
  );
}
```

### Hook Typing
```typescript
// ✅ CORRECT: Custom hook with proper typing
interface UseApiOptions<T> {
  initialData?: T;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

interface UseApiReturn<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

function useApi<T>(
  url: string, 
  options: UseApiOptions<T> = {}
): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(options.initialData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json() as T;
      setData(result);
      options.onSuccess?.(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      options.onError?.(error);
    } finally {
      setLoading(false);
    }
  }, [url, options]);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  return { data, loading, error, refetch: fetchData };
}
```

## 🗄️ Backend TypeScript Patterns

### Express + TypeScript
```typescript
// ✅ CORRECT: Typed Express interfaces
interface AuthenticatedRequest extends Request {
  user: User;
  correlationId: string;
}

interface TypedResponse<T> extends Response {
  json(body: ApiResponse<T>): this;
}

// ✅ CORRECT: Typed route handlers
type RouteHandler<TRequest = {}, TResponse = unknown> = (
  req: Request & TRequest,
  res: TypedResponse<TResponse>,
  next: NextFunction
) => Promise<void> | void;

const getUserById: RouteHandler<
  { params: { id: string } },
  User
> = async (req, res) => {
  const userId = req.params.id;
  const user = await userService.findById(userId);
  
  if (!user) {
    return res.status(404).json({
      success: false,
      error: { code: 'USER_NOT_FOUND', message: 'User not found' }
    });
  }
  
  res.json({
    success: true,
    data: user
  });
};
```

### Service Layer Typing
```typescript
// ✅ CORRECT: Service interface definitions
interface UserService {
  findById(id: string): Promise<User | null>;
  findByEmail(email: string): Promise<User | null>;
  create(userData: CreateUserRequest): Promise<User>;
  update(id: string, updates: UpdateUserRequest): Promise<User>;
  delete(id: string): Promise<void>;
  list(options: ListOptions): Promise<PaginatedResult<User>>;
}

interface ListOptions {
  page?: number;
  limit?: number;
  sortBy?: keyof User;
  sortOrder?: 'asc' | 'desc';
  filters?: Partial<User>;
}

interface PaginatedResult<T> {
  items: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

// ✅ CORRECT: Implementation with dependency injection
class UserServiceImpl implements UserService {
  constructor(
    private readonly userRepository: UserRepository,
    private readonly logger: Logger,
    private readonly cacheService: CacheService
  ) {}
  
  async findById(id: string): Promise<User | null> {
    const cacheKey = `user:${id}`;
    const cached = await this.cacheService.get<User>(cacheKey);
    
    if (cached) {
      this.logger.debug('User found in cache', { userId: id });
      return cached;
    }
    
    const user = await this.userRepository.findById(id);
    if (user) {
      await this.cacheService.set(cacheKey, user, 3600);
    }
    
    return user;
  }
}
```

## 🔧 Configuration & Environment Typing

### Environment Variables
```typescript
// ✅ CORRECT: Typed environment configuration
import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'staging', 'production']),
  PORT: z.coerce.number().min(1000).max(65535).default(5000),
  
  // Database
  MONGO_URI: z.string().url(),
  MONGO_DB_NAME: z.string().min(1),
  
  // Redis
  REDIS_URL: z.string().url(),
  REDIS_TTL: z.coerce.number().positive().default(3600),
  
  // JWT
  JWT_ACCESS_SECRET: z.string().min(32),
  JWT_REFRESH_SECRET: z.string().min(32),
  JWT_ACCESS_EXPIRES_IN: z.string().default('15m'),
  JWT_REFRESH_EXPIRES_IN: z.string().default('7d'),
  
  // External APIs
  OPENWEATHERMAP_API_KEY: z.string().optional(),
  
  // Security
  ALLOWED_ORIGINS: z.string().transform(s => s.split(',')),
  RATE_LIMIT_WINDOW_MS: z.coerce.number().positive().default(900000),
  RATE_LIMIT_MAX_REQUESTS: z.coerce.number().positive().default(100),
  
  // Logging
  LOG_LEVEL: z.enum(['error', 'warn', 'info', 'debug']).default('info'),
});

export type Environment = z.infer<typeof envSchema>;

// Validate and export typed environment
export const env: Environment = envSchema.parse(process.env);

// Usage with type safety
const dbConfig = {
  uri: env.MONGO_URI,
  dbName: env.MONGO_DB_NAME,
  options: {
    maxPoolSize: 10,
    serverSelectionTimeoutMS: 5000,
  }
};
```

## 🧪 Testing with TypeScript

### Test Type Definitions
```typescript
// ✅ CORRECT: Typed test utilities
interface TestUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

interface MockUserService extends UserService {
  __setMockUsers(users: TestUser[]): void;
  __getMockCalls(): Array<{ method: string; args: unknown[] }>;
}

// ✅ CORRECT: Factory functions with types
function createTestUser(overrides: Partial<TestUser> = {}): TestUser {
  return {
    id: crypto.randomUUID(),
    name: 'Test User',
    email: 'test@example.com',
    role: 'user',
    ...overrides,
  };
}

function createMockUserService(): MockUserService {
  const mockCalls: Array<{ method: string; args: unknown[] }> = [];
  let mockUsers: TestUser[] = [];
  
  return {
    async findById(id: string) {
      mockCalls.push({ method: 'findById', args: [id] });
      return mockUsers.find(user => user.id === id) || null;
    },
    
    async create(userData: CreateUserRequest) {
      mockCalls.push({ method: 'create', args: [userData] });
      const user = createTestUser(userData);
      mockUsers.push(user);
      return user;
    },
    
    __setMockUsers(users: TestUser[]) {
      mockUsers = users;
    },
    
    __getMockCalls() {
      return mockCalls;
    },
    
    // ... other methods
  } as MockUserService;
}
```

## 🚨 Common TypeScript Anti-Patterns

### Avoid These Patterns
```typescript
// ❌ AVOID: Any types
function processData(data: any): any {
  return data.someProperty;
}

// ✅ USE: Generic constraints
function processData<T extends { someProperty: unknown }>(data: T): T['someProperty'] {
  return data.someProperty;
}

// ❌ AVOID: Type assertions without validation
const user = req.body as User;

// ✅ USE: Runtime validation
const parseResult = UserSchema.safeParse(req.body);
if (!parseResult.success) {
  throw new ValidationError('Invalid user data');
}
const user = parseResult.data;

// ❌ AVOID: Non-null assertion without certainty
const user = users.find(u => u.id === id)!;

// ✅ USE: Proper null checking
const user = users.find(u => u.id === id);
if (!user) {
  throw new NotFoundError('User not found');
}

// ❌ AVOID: Implicit any in function parameters
function handleEvent(event) {
  console.log(event.type);
}

// ✅ USE: Explicit typing
interface Event {
  type: string;
  timestamp: Date;
  data?: Record<string, unknown>;
}

function handleEvent(event: Event): void {
  console.log(event.type);
}
```

## 📊 Type Performance Considerations

### Efficient Type Definitions
```typescript
// ✅ EFFICIENT: Use const assertions for literal types
const USER_ROLES = ['user', 'admin', 'moderator'] as const;
type UserRole = typeof USER_ROLES[number];

// ✅ EFFICIENT: Use mapped types for transformations
type Optional<T> = {
  [K in keyof T]?: T[K];
};

type Required<T> = {
  [K in keyof T]-?: T[K];
};

// ✅ EFFICIENT: Use conditional types sparingly
type NonNullable<T> = T extends null | undefined ? never : T;

// ❌ INEFFICIENT: Deeply nested conditional types
type DeepComplexType<T> = T extends string
  ? T extends `${infer A}${infer B}`
    ? B extends `${infer C}${infer D}`
      ? // ... many more levels
      : never
    : never
  : never;
```

## 🔍 TypeScript Compiler Optimization

### tsconfig.json Performance Settings
```json
{
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": ".tsbuildinfo",
    "skipLibCheck": true,
    "skipDefaultLibCheck": true,
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": [
    "node_modules",
    "dist",
    "**/*.test.ts",
    "**/*.spec.ts"
  ]
}
```

---

**Remember**: TypeScript is a tool for developer productivity and code safety. Use it to catch errors at compile time, improve code documentation, and enable better IDE support. Always prioritize type safety over convenience.