from datetime import datetime, timedelta
from typing import List, Optional
from sqlmodel import Session, select, func
from sqlalchemy import and_

from app.models.metric import (
    ApiMetric,
    ApiMetricRead,
    MetricsSummary,
    EndpointStats,
    ErrorStats
)


class MetricsService:
    """
    Service for querying and aggregating API metrics.

    Provides analytics and statistics from stored metrics.
    """

    def get_recent_metrics(
        self,
        session: Session,
        limit: int = 100,
        hours: Optional[int] = None
    ) -> List[ApiMetric]:
        """
        Get recent API metrics.

        Args:
            session: Database session
            limit: Maximum number of records
            hours: Filter last N hours (optional)

        Returns:
            List of recent metrics
        """
        statement = select(ApiMetric).order_by(ApiMetric.timestamp.desc()).limit(limit)

        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            statement = statement.where(ApiMetric.timestamp >= cutoff)

        return list(session.exec(statement).all())

    def get_summary(
        self,
        session: Session,
        hours: Optional[int] = 24
    ) -> MetricsSummary:
        """
        Get aggregated metrics summary.

        Args:
            session: Database session
            hours: Time window in hours (default: 24h)

        Returns:
            Summary with totals, averages, and percentiles
        """
        # Build query with time filter
        filters = []
        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            filters.append(ApiMetric.timestamp >= cutoff)

        # Total requests
        total_query = select(func.count(ApiMetric.id))
        if filters:
            total_query = total_query.where(and_(*filters))
        total_requests = session.exec(total_query).one()

        # Successful requests (2xx and 3xx)
        success_query = select(func.count(ApiMetric.id)).where(
            ApiMetric.status_code < 400
        )
        if filters:
            success_query = success_query.where(and_(*filters))
        successful_requests = session.exec(success_query).one()

        # Failed requests (4xx and 5xx)
        failed_requests = total_requests - successful_requests

        # Duration stats
        duration_query = select(
            func.avg(ApiMetric.duration_ms),
            func.min(ApiMetric.duration_ms),
            func.max(ApiMetric.duration_ms)
        )
        if filters:
            duration_query = duration_query.where(and_(*filters))

        result = session.exec(duration_query).one()
        avg_duration, min_duration, max_duration = result

        # Percentiles (p50, p95, p99) - requires getting all durations
        # For large datasets, this should be optimized with sampling
        durations_query = select(ApiMetric.duration_ms)
        if filters:
            durations_query = durations_query.where(and_(*filters))
        durations_query = durations_query.order_by(ApiMetric.duration_ms)

        durations = list(session.exec(durations_query).all())

        p50 = self._percentile(durations, 50) if durations else None
        p95 = self._percentile(durations, 95) if durations else None
        p99 = self._percentile(durations, 99) if durations else None

        return MetricsSummary(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_duration_ms=round(avg_duration, 2) if avg_duration else 0.0,
            min_duration_ms=round(min_duration, 2) if min_duration else 0.0,
            max_duration_ms=round(max_duration, 2) if max_duration else 0.0,
            p50_duration_ms=round(p50, 2) if p50 else None,
            p95_duration_ms=round(p95, 2) if p95 else None,
            p99_duration_ms=round(p99, 2) if p99 else None
        )

    def get_endpoint_stats(
        self,
        session: Session,
        hours: Optional[int] = 24,
        limit: int = 20
    ) -> List[EndpointStats]:
        """
        Get statistics per endpoint.

        Args:
            session: Database session
            hours: Time window in hours
            limit: Max number of endpoints to return

        Returns:
            List of endpoint statistics ordered by request count
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours) if hours else None

        # Query grouped by endpoint and method
        total_requests_col = func.count(ApiMetric.id).label("total_requests")
        avg_duration_col = func.avg(ApiMetric.duration_ms).label("avg_duration")

        query = select(
            ApiMetric.path,
            ApiMetric.method,
            total_requests_col,
            avg_duration_col
        ).group_by(ApiMetric.path, ApiMetric.method)

        if cutoff:
            query = query.where(ApiMetric.timestamp >= cutoff)

        query = query.order_by(total_requests_col.desc()).limit(limit)

        results = session.exec(query).all()

        stats = []
        for row in results:
            path, method, total, avg_dur = row

            # Count errors separately for this endpoint
            error_query = select(func.count(ApiMetric.id)).where(
                and_(
                    ApiMetric.path == path,
                    ApiMetric.method == method,
                    ApiMetric.status_code >= 400
                )
            )
            if cutoff:
                error_query = error_query.where(ApiMetric.timestamp >= cutoff)

            errors = session.exec(error_query).one()
            error_rate = (errors / total * 100) if total > 0 else 0
            success_rate = 100 - error_rate

            stats.append(EndpointStats(
                endpoint=path,
                method=method,
                total_requests=total,
                avg_duration_ms=round(avg_dur, 2) if avg_dur else 0.0,
                error_rate=round(error_rate, 2),
                success_rate=round(success_rate, 2)
            ))

        return stats

    def get_error_stats(
        self,
        session: Session,
        hours: Optional[int] = 24
    ) -> List[ErrorStats]:
        """
        Get error statistics grouped by status code.

        Args:
            session: Database session
            hours: Time window in hours

        Returns:
            List of error statistics
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours) if hours else None

        # Get total requests for percentage calculation
        total_query = select(func.count(ApiMetric.id))
        if cutoff:
            total_query = total_query.where(ApiMetric.timestamp >= cutoff)
        total_requests = session.exec(total_query).one()

        # Query grouped by status code (only errors)
        count_col = func.count(ApiMetric.id).label("count")

        query = select(
            ApiMetric.status_code,
            count_col
        ).where(
            ApiMetric.status_code >= 400
        ).group_by(ApiMetric.status_code)

        if cutoff:
            query = query.where(ApiMetric.timestamp >= cutoff)

        query = query.order_by(count_col.desc())

        results = session.exec(query).all()

        stats = []
        for status_code, count in results:
            percentage = (count / total_requests * 100) if total_requests > 0 else 0

            # Get most common path for this status code
            path_count_col = func.count(ApiMetric.id).label("count")
            path_query = select(
                ApiMetric.path,
                path_count_col
            ).where(
                ApiMetric.status_code == status_code
            ).group_by(ApiMetric.path).order_by(path_count_col.desc()).limit(1)

            if cutoff:
                path_query = path_query.where(ApiMetric.timestamp >= cutoff)

            path_result = session.exec(path_query).first()
            most_common_path = path_result[0] if path_result else None

            stats.append(ErrorStats(
                status_code=status_code,
                count=count,
                percentage=round(percentage, 2),
                most_common_path=most_common_path
            ))

        return stats

    def get_slowest_endpoints(
        self,
        session: Session,
        hours: Optional[int] = 24,
        limit: int = 10
    ) -> List[EndpointStats]:
        """
        Get slowest endpoints by average duration.

        Args:
            session: Database session
            hours: Time window in hours
            limit: Max number of endpoints

        Returns:
            List of endpoints ordered by average duration (slowest first)
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours) if hours else None

        total_requests_col = func.count(ApiMetric.id).label("total_requests")
        avg_duration_col = func.avg(ApiMetric.duration_ms).label("avg_duration")

        query = select(
            ApiMetric.path,
            ApiMetric.method,
            total_requests_col,
            avg_duration_col
        ).group_by(ApiMetric.path, ApiMetric.method)

        if cutoff:
            query = query.where(ApiMetric.timestamp >= cutoff)

        # Only consider endpoints with at least 10 requests (avoid outliers)
        query = query.having(func.count(ApiMetric.id) >= 10)
        query = query.order_by(avg_duration_col.desc()).limit(limit)

        results = session.exec(query).all()

        stats = []
        for path, method, total, avg_dur in results:
            stats.append(EndpointStats(
                endpoint=path,
                method=method,
                total_requests=total,
                avg_duration_ms=round(avg_dur, 2) if avg_dur else 0.0,
                error_rate=0.0,  # Not calculated for this query
                success_rate=0.0
            ))

        return stats

    def _percentile(self, data: List[float], percentile: int) -> Optional[float]:
        """Calculate percentile from sorted data"""
        if not data:
            return None

        k = (len(data) - 1) * (percentile / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f

        if f == c:
            return data[f]

        # Linear interpolation
        d0 = data[f] * (c - k)
        d1 = data[c] * (k - f)
        return d0 + d1


# Singleton instance
metrics_service = MetricsService()
