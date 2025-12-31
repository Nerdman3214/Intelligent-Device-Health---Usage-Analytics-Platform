package com.apple.telemetry.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Builder;
import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * Device health analysis response.
 * 
 * Apple principle: Responses must be explainable and actionable.
 * 
 * Every prediction includes:
 * - Risk level (HEALTHY, AT_RISK, DEGRADED)
 * - Confidence score
 * - Probabilities for each risk level
 * - Top contributing features (explainability)
 * - Warnings (if any)
 */
@Data
@Builder
public class DeviceHealthResponse {
    
    @JsonProperty("device_id")
    private String deviceId;
    
    @JsonProperty("predicted_risk")
    private String predictedRisk;
    
    @JsonProperty("confidence")
    private Double confidence;
    
    @JsonProperty("probabilities")
    private Map<String, Double> probabilities;
    
    @JsonProperty("is_confident")
    private Boolean isConfident;
    
    @JsonProperty("is_in_distribution")
    private Boolean isInDistribution;
    
    @JsonProperty("top_contributing_features")
    private List<FeatureContribution> topContributingFeatures;
    
    @JsonProperty("warnings")
    private List<String> warnings;
    
    @JsonProperty("explanation_text")
    private String explanationText;
    
    @JsonProperty("model_version")
    private String modelVersion;
    
    @Data
    @Builder
    public static class FeatureContribution {
        private String feature;
        private Double value;
        private Double contribution;
        private String direction;
    }
}
