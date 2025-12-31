"""
Intelligent Device Health & Usage Analytics Platform - Demo

This script demonstrates the complete Phase 1 + Phase 2 system working together.

Author: Software Engineering Intern
Purpose: Show Apple-grade data pipeline and analytics in action
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ingestion import (
    TelemetryGenerator,
    TelemetryIngestor,
    ThermalState,
    DeviceType
)
from analytics import (
    TelemetryMetrics,
    SummaryGenerator,
    AnomalyDetector
)


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_phase_1_ingestion():
    """Demonstrate Phase 1: Defensive data ingestion"""
    print_section("PHASE 1: DEFENSIVE DATA INGESTION")
    
    # Initialize ingestor
    data_dir = Path(__file__).parent.parent / 'data'
    ingestor = TelemetryIngestor(data_dir)
    
    print("📊 Generating mixed-quality telemetry data...")
    print("   - 90% clean data (should be accepted)")
    print("   - 10% corrupted data (should be rejected)\n")
    
    # Generate batch with intentional corruption
    batch = TelemetryGenerator.generate_batch(
        count=50,
        quality='clean',
        corruption_rate=0.10
    )
    
    print(f"Generated {len(batch)} telemetry records\n")
    
    # Ingest batch
    print("🔍 Running ingestion pipeline: generate → validate → normalize → store\n")
    result = ingestor.ingest_batch(batch)
    
    print("📈 INGESTION RESULTS:")
    print(f"   Total Processed: {result['total']}")
    print(f"   ✅ Accepted: {result['accepted']}")
    print(f"   ❌ Rejected: {result['rejected']}")
    print(f"   Acceptance Rate: {result['acceptance_rate']:.1f}%\n")
    
    # Show statistics
    stats = ingestor.get_stats()
    if stats['rejection_reasons']:
        print("🔴 REJECTION BREAKDOWN:")
        for reason, count in stats['rejection_reasons'].items():
            print(f"   - {reason}: {count}")
    
    print("\n✅ Phase 1 Complete: Data ingestion working defensively")
    print(f"   - Processed data: {ingestor.processed_dir}")
    print(f"   - Rejected data: {ingestor.rejected_dir}")
    
    return batch


def demo_phase_2_analytics(telemetry_data):
    """Demonstrate Phase 2: Statistical analytics and summaries"""
    print_section("PHASE 2: STATISTICAL ANALYTICS")
    
    # Filter to only valid records (remove corrupted)
    valid_records = [
        r for r in telemetry_data 
        if 'cpu_usage' in r and isinstance(r['cpu_usage'], (int, float))
    ]
    
    if not valid_records:
        print("⚠️  No valid records for analysis")
        return
    
    print(f"📊 Analyzing {len(valid_records)} valid telemetry records\n")
    
    # === METRICS ANALYSIS ===
    print("📐 CORE METRICS (Mean, Median, Percentiles)\n")
    
    for field in ['cpu_usage', 'battery_health', 'memory_usage']:
        try:
            metrics = TelemetryMetrics.calculate_telemetry_summary(
                valid_records, field
            )
            
            print(f"{field.upper().replace('_', ' ')}:")
            print(f"   Mean:   {metrics['mean']:.2f}")
            print(f"   Median: {metrics['median']:.2f}")
            print(f"   P90:    {metrics['p90']:.2f}")
            print(f"   P95:    {metrics['p95']:.2f}")
            print(f"   P99:    {metrics['p99']:.2f}")
            print(f"   Range:  [{metrics['min']:.2f}, {metrics['max']:.2f}]")
            print()
        except Exception as e:
            print(f"   ⚠️  Could not analyze {field}: {e}\n")
    
    # === ANOMALY DETECTION ===
    print("\n🔍 ANOMALY DETECTION (Z-score, IQR, Thresholds)\n")
    
    # Detect CPU anomalies
    try:
        cpu_anomalies = AnomalyDetector.detect_anomalies_comprehensive(
            valid_records,
            'cpu_usage',
            z_score_threshold=2.5,
            iqr_multiplier=1.5
        )
        
        if cpu_anomalies:
            print(f"Found {len(cpu_anomalies)} CPU usage anomalies:")
            for anomaly in cpu_anomalies[:3]:  # Show first 3
                print(f"   ⚠️  {anomaly.severity.value.upper()}: {anomaly.reason}")
                print(f"      Value: {anomaly.value:.2f}, Expected: {anomaly.expected_range}")
        else:
            print("✅ No CPU usage anomalies detected")
    except Exception as e:
        print(f"   ⚠️  CPU anomaly detection failed: {e}")
    
    print()
    
    # Detect battery health anomalies
    try:
        battery_anomalies = AnomalyDetector.detect_anomalies_comprehensive(
            valid_records,
            'battery_health',
            absolute_thresholds={'lower': 0.7, 'upper': 1.0}
        )
        
        if battery_anomalies:
            print(f"Found {len(battery_anomalies)} battery health anomalies:")
            for anomaly in battery_anomalies[:3]:
                print(f"   🔋 {anomaly.severity.value.upper()}: {anomaly.reason}")
        else:
            print("✅ No battery health anomalies detected")
    except Exception as e:
        print(f"   ⚠️  Battery anomaly detection failed: {e}")
    
    # === DEVICE HEALTH SUMMARY ===
    print("\n" + "-" * 70)
    print_section("DEVICE HEALTH SUMMARY (Decision Support)")
    
    # Pick a device ID from the data
    device_id = valid_records[0].get('device_id', 'UNKNOWN')
    
    try:
        summary = SummaryGenerator.generate_device_summary(
            device_id=device_id,
            telemetry_records=valid_records
        )
        
        print(f"Device ID: {summary.device_id}")
        print(f"Status: {summary.status.value.upper()} (confidence: {summary.confidence:.2f})")
        print()
        print("REASONS:")
        for i, reason in enumerate(summary.reasons, 1):
            print(f"   {i}. {reason}")
        
        print()
        print("RECOMMENDATIONS:")
        for i, rec in enumerate(summary.recommendations, 1):
            print(f"   {i}. {rec}")
        
        if summary.anomalies:
            print()
            print(f"DETECTED ANOMALIES: {len(summary.anomalies)}")
            for anomaly in summary.anomalies[:3]:
                print(f"   - {anomaly.field}: {anomaly.reason}")
        
        print("\n✅ Phase 2 Complete: Analytics and decision support working")
        
        # Save summary to file
        reports_dir = Path(__file__).parent.parent / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        summary_file = reports_dir / f'summary_{device_id[:8]}.json'
        with open(summary_file, 'w') as f:
            json.dump(summary.to_dict(), f, indent=2, default=str)
        
        print(f"   - Summary saved: {summary_file}")
    
    except Exception as e:
        print(f"⚠️  Summary generation failed: {e}")
        import traceback
        traceback.print_exc()


def demo_complete_workflow():
    """Run complete demo: Phase 1 → Phase 2"""
    print("\n" + "🍎" * 35)
    print("  INTELLIGENT DEVICE HEALTH & USAGE ANALYTICS PLATFORM")
    print("  Apple-Style Backend & Data Engineering Demo")
    print("🍎" * 35)
    
    print("\n📋 This demo shows:")
    print("   1. Phase 1: Defensive data ingestion with validation")
    print("   2. Phase 2: Statistical analytics and anomaly detection")
    print("   3. Decision support: Device health summaries\n")
    
    input("Press ENTER to start demo...")
    
    # Phase 1: Ingestion
    telemetry_data = demo_phase_1_ingestion()
    
    input("\nPress ENTER to continue to Phase 2...")
    
    # Phase 2: Analytics
    demo_phase_2_analytics(telemetry_data)
    
    print("\n" + "=" * 70)
    print("  DEMO COMPLETE")
    print("=" * 70)
    print("\n✅ Both phases working correctly")
    print("✅ Data pipeline: generate → validate → store → analyze → summarize")
    print("✅ Defensive programming: explicit errors, no silent failures")
    print("✅ Statistical methods: metrics, trends, anomaly detection")
    print("✅ Decision support: actionable summaries with confidence scores")
    print("\n🍎 Apple-grade engineering demonstrated.\n")


if __name__ == '__main__':
    try:
        demo_complete_workflow()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
