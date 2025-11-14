/**
 * API Versioning Strategy for SMC Trading Agent
 * Implements comprehensive versioning with backward compatibility
 */

import { Request, Response, NextFunction } from 'express';

// API version configuration
export const API_VERSIONS = {
  V1: 'v1',
  V2: 'v2', // Future version
  LATEST: 'v1'
} as const;

export type ApiVersion = typeof API_VERSIONS[keyof typeof API_VERSIONS];

// Version compatibility matrix
export const VERSION_COMPATIBILITY = {
  [API_VERSIONS.V1]: {
    supported: true,
    deprecated: false,
    sunset_date: null,
    breaking_changes: [],
    migration_guide: null
  },
  [API_VERSIONS.V2]: {
    supported: false, // Future version
    deprecated: false,
    sunset_date: null,
    breaking_changes: [
      'Authentication method changed to OAuth2',
      'Response format standardized',
      'Error codes restructured'
    ],
    migration_guide: '/docs/migration/v1-to-v2'
  }
} as const;

// Version detection strategies
export enum VersionStrategy {
  URL_PATH = 'url_path',           // /api/v1/endpoint
  HEADER = 'header',               // X-API-Version: v1
  QUERY_PARAM = 'query_param',     // ?version=v1
  ACCEPT_HEADER = 'accept_header'  // Accept: application/vnd.smc.v1+json
}

// Default versioning configuration
export const VERSIONING_CONFIG = {
  strategy: VersionStrategy.URL_PATH,
  default_version: API_VERSIONS.V1,
  header_name: 'X-API-Version',
  query_param_name: 'version',
  accept_header_prefix: 'application/vnd.smc',
  strict_versioning: false, // Allow requests without version specification
  version_in_response: true // Include version in response headers
};

/**
 * Extract API version from request based on strategy
 */
export function extractVersionFromRequest(req: Request, strategy: VersionStrategy = VERSIONING_CONFIG.strategy): ApiVersion | null {
  switch (strategy) {
    case VersionStrategy.URL_PATH:
      // Extract from URL path: /api/v1/endpoint
      const pathMatch = req.path.match(/^\/api\/(v\d+)\//);
      return pathMatch ? pathMatch[1] as ApiVersion : null;

    case VersionStrategy.HEADER:
      // Extract from custom header: X-API-Version: v1
      const headerVersion = req.headers[VERSIONING_CONFIG.header_name.toLowerCase()] as string;
      return headerVersion as ApiVersion || null;

    case VersionStrategy.QUERY_PARAM:
      // Extract from query parameter: ?version=v1
      const queryVersion = req.query[VERSIONING_CONFIG.query_param_name] as string;
      return queryVersion as ApiVersion || null;

    case VersionStrategy.ACCEPT_HEADER:
      // Extract from Accept header: Accept: application/vnd.smc.v1+json
      const acceptHeader = req.headers.accept;
      if (acceptHeader) {
        const acceptMatch = acceptHeader.match(new RegExp(`${VERSIONING_CONFIG.accept_header_prefix}\\.(v\\d+)\\+json`));
        return acceptMatch ? acceptMatch[1] as ApiVersion : null;
      }
      return null;

    default:
      return null;
  }
}

/**
 * Validate if a version is supported
 */
export function isVersionSupported(version: ApiVersion): boolean {
  return VERSION_COMPATIBILITY[version]?.supported || false;
}

/**
 * Check if a version is deprecated
 */
export function isVersionDeprecated(version: ApiVersion): boolean {
  return VERSION_COMPATIBILITY[version]?.deprecated || false;
}

/**
 * Get version information
 */
export function getVersionInfo(version: ApiVersion) {
  return VERSION_COMPATIBILITY[version] || null;
}

/**
 * Version detection middleware
 */
export function versionDetectionMiddleware(req: Request, res: Response, next: NextFunction) {
  // Try to extract version using configured strategy
  let detectedVersion = extractVersionFromRequest(req, VERSIONING_CONFIG.strategy);
  
  // Fallback to other strategies if primary fails
  if (!detectedVersion) {
    for (const strategy of Object.values(VersionStrategy)) {
      if (strategy !== VERSIONING_CONFIG.strategy) {
        detectedVersion = extractVersionFromRequest(req, strategy);
        if (detectedVersion) break;
      }
    }
  }
  
  // Use default version if none detected and strict versioning is disabled
  const version = detectedVersion || (VERSIONING_CONFIG.strict_versioning ? null : VERSIONING_CONFIG.default_version);
  
  // Validate version
  if (!version) {
    return res.status(400).json({
      success: false,
      error: 'API version is required',
      details: `Specify version using ${VERSIONING_CONFIG.strategy}`,
      supported_versions: Object.values(API_VERSIONS).filter(v => isVersionSupported(v)),
      code: 'VERSION_REQUIRED'
    });
  }
  
  if (!isVersionSupported(version)) {
    return res.status(400).json({
      success: false,
      error: 'Unsupported API version',
      details: `Version ${version} is not supported`,
      supported_versions: Object.values(API_VERSIONS).filter(v => isVersionSupported(v)),
      code: 'UNSUPPORTED_VERSION'
    });
  }
  
  // Add version information to request
  (req as any).apiVersion = version;
  (req as any).versionInfo = getVersionInfo(version);
  
  // Add version to response headers if configured
  if (VERSIONING_CONFIG.version_in_response) {
    res.setHeader('X-API-Version', version);
    res.setHeader('X-API-Version-Status', isVersionDeprecated(version) ? 'deprecated' : 'current');
  }
  
  // Add deprecation warning if version is deprecated
  if (isVersionDeprecated(version)) {
    const versionInfo = getVersionInfo(version);
    res.setHeader('Warning', `299 - "API version ${version} is deprecated"`);
    if (versionInfo?.sunset_date) {
      res.setHeader('Sunset', versionInfo.sunset_date);
    }
  }
  
  next();
}

/**
 * Version-specific route handler wrapper
 */
export function versionedRoute(version: ApiVersion, handler: (req: Request, res: Response, next: NextFunction) => void) {
  return (req: Request, res: Response, next: NextFunction) => {
    const requestVersion = (req as any).apiVersion;
    
    if (requestVersion === version) {
      return handler(req, res, next);
    }
    
    // Version mismatch - this shouldn't happen if middleware is properly configured
    return res.status(400).json({
      success: false,
      error: 'Version mismatch',
      details: `Expected ${version}, got ${requestVersion}`,
      code: 'VERSION_MISMATCH'
    });
  };
}

/**
 * Create version-specific router
 */
export function createVersionedRouter(version: ApiVersion) {
  const express = require('express');
  const router = express.Router();
  
  // Add version validation middleware to all routes in this router
  router.use((req: Request, res: Response, next: NextFunction) => {
    const requestVersion = (req as any).apiVersion;
    if (requestVersion !== version) {
      return res.status(400).json({
        success: false,
        error: 'Version mismatch',
        details: `This router handles ${version}, got ${requestVersion}`,
        code: 'VERSION_MISMATCH'
      });
    }
    next();
  });
  
  return router;
}

/**
 * Response transformation middleware for version compatibility
 */
export function responseTransformMiddleware(req: Request, res: Response, next: NextFunction) {
  const version = (req as any).apiVersion;
  const originalJson = res.json;
  
  // Override res.json to transform responses based on version
  res.json = function(data: any) {
    const transformedData = transformResponseForVersion(data, version);
    return originalJson.call(this, transformedData);
  };
  
  next();
}

/**
 * Transform response data based on API version
 */
function transformResponseForVersion(data: any, version: ApiVersion): any {
  switch (version) {
    case API_VERSIONS.V1:
      // V1 response format - current format
      return data;
      
    case API_VERSIONS.V2:
      // V2 response format - future format with standardized structure
      if (data && typeof data === 'object') {
        return {
          data: data,
          meta: {
            version: version,
            timestamp: new Date().toISOString(),
            request_id: Math.random().toString(36).substr(2, 9)
          }
        };
      }
      return data;
      
    default:
      return data;
  }
}

/**
 * Get API version information endpoint
 */
export function getVersionInfoEndpoint(req: Request, res: Response) {
  const currentVersion = (req as any).apiVersion || VERSIONING_CONFIG.default_version;
  
  const versionInfo = {
    current_version: currentVersion,
    supported_versions: Object.entries(VERSION_COMPATIBILITY)
      .filter(([_, info]) => info.supported)
      .map(([version, info]) => ({
        version,
        deprecated: info.deprecated,
        sunset_date: info.sunset_date,
        migration_guide: info.migration_guide
      })),
    versioning_strategy: VERSIONING_CONFIG.strategy,
    documentation: {
      openapi_spec: `/api/${currentVersion}/openapi.json`,
      swagger_ui: `/api/${currentVersion}/docs`,
      redoc: `/api/${currentVersion}/redoc`
    }
  };
  
  res.json({
    success: true,
    data: versionInfo
  });
}

/**
 * Migration guide endpoint
 */
export function getMigrationGuideEndpoint(req: Request, res: Response) {
  const { from, to } = req.params;
  
  const fromInfo = getVersionInfo(from as ApiVersion);
  const toInfo = getVersionInfo(to as ApiVersion);
  
  if (!fromInfo || !toInfo) {
    return res.status(404).json({
      success: false,
      error: 'Version not found',
      code: 'VERSION_NOT_FOUND'
    });
  }
  
  const migrationGuide = {
    from_version: from,
    to_version: to,
    breaking_changes: toInfo.breaking_changes,
    migration_steps: [
      'Update API version in requests',
      'Review breaking changes',
      'Update request/response handling',
      'Test thoroughly in staging environment'
    ],
    estimated_effort: 'Medium',
    support_until: fromInfo.sunset_date,
    documentation: toInfo.migration_guide
  };
  
  res.json({
    success: true,
    data: migrationGuide
  });
}

// Export all versioning utilities
export default {
  API_VERSIONS,
  VERSION_COMPATIBILITY,
  VERSIONING_CONFIG,
  VersionStrategy,
  extractVersionFromRequest,
  isVersionSupported,
  isVersionDeprecated,
  getVersionInfo,
  versionDetectionMiddleware,
  versionedRoute,
  createVersionedRouter,
  responseTransformMiddleware,
  getVersionInfoEndpoint,
  getMigrationGuideEndpoint
};