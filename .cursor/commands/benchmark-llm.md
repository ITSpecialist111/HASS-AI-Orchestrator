# Benchmark LLM Performance

## Purpose
Tests and compares LLM performance across different models and providers to optimize agent decision speed and quality.

## Usage
`/benchmark-llm [models] [--iterations=10]`

Examples:
- `/benchmark-llm` - Test all configured models
- `/benchmark-llm deepseek-r1:8b mistral:7b --iterations=20`
- `/benchmark-llm gemini-pro --detailed`

## Instructions for Agent

When this command is invoked:

1. **Identify Models to Test**:
   - List all models in agents.yaml
   - Include Ollama models: `ollama list`
   - Include Gemini if API key configured
   - Filter by specified models if provided

2. **Prepare Test Scenarios**:
   
   **Scenario 1: Simple Decision**:
   ```
   Context: Temperature is 22°C, target is 21°C
   Task: Decide if adjustment needed
   Expected: Single action decision
   ```
   
   **Scenario 2: Complex Reasoning**:
   ```
   Context: Multiple rooms, varying temps, occupancy
   Task: Optimize heating across all zones
   Expected: Multi-step reasoning
   ```
   
   **Scenario 3: RAG Query**:
   ```
   Context: User manual question
   Task: Answer based on knowledge base
   Expected: Retrieval + generation
   ```

3. **Run Benchmarks**:
   
   For each model, measure:
   - **Cold Start**: First inference (model loading)
   - **Warm Inference**: Subsequent calls
   - **Token Speed**: Tokens per second
   - **Total Latency**: End-to-end time
   - **Memory Usage**: Peak RAM/VRAM
   - **CPU/GPU Utilization**: During inference

4. **Test Matrix**:
   ```
   For each model:
     For each scenario:
       For N iterations:
         - Record inference time
         - Measure token generation speed
         - Check response quality
         - Monitor resource usage
   ```

5. **Quality Assessment**:
   - Parse JSON response success rate
   - Decision quality (manual review sample)
   - Hallucination detection
   - Instruction following accuracy
   - Output format compliance

6. **Generate Performance Report**:
   ```markdown
   # LLM Benchmark Report
   Generated: [timestamp]
   Iterations per test: [N]
   
   ## Models Tested
   - [model1] (Ollama)
   - [model2] (Ollama)
   - [model3] (Gemini)
   
   ## Performance Summary
   
   | Model | Avg Latency | Tokens/sec | Quality | Memory |
   |-------|-------------|------------|---------|---------|
   | deepseek-r1:8b | 1.2s | 45 t/s | 9.5/10 | 8.5GB |
   | mistral:7b | 0.8s | 60 t/s | 8.0/10 | 6.2GB |
   | gemini-pro | 2.1s | 35 t/s | 9.8/10 | N/A |
   
   ## Detailed Results
   
   ### [Model Name]
   - Cold Start: [X]s
   - Warm Avg: [X]s
   - Token Speed: [X] tokens/sec
   - Success Rate: [X]%
   - Peak Memory: [X]GB
   
   [Scenario breakdown]
   
   ## Recommendations
   
   ### For Speed (Real-time agents):
   Use [model] - fastest inference
   
   ### For Quality (Complex decisions):
   Use [model] - best reasoning
   
   ### For Efficiency (Resource-constrained):
   Use [model] - best performance/resource ratio
   ```

7. **Statistical Analysis**:
   - Calculate mean, median, std dev
   - Identify outliers
   - Compare distributions
   - Test statistical significance

8. **Cost Analysis** (if using paid APIs):
   - Tokens consumed per decision
   - Cost per 1000 decisions
   - Monthly cost estimates
   - Compare with local alternatives

9. **Resource Profiling**:
   - CPU usage patterns
   - GPU utilization (if available)
   - Memory peaks
   - Disk I/O
   - Network latency (for remote APIs)

10. **Create Visualizations**:
    - Latency distribution chart
    - Token speed comparison
    - Memory usage over time
    - Quality vs speed scatter plot

11. **Model Recommendations**:
    
    **By Use Case**:
    - Real-time agents (5-10s interval): [fastest model]
    - Standard agents (60-120s): [balanced model]
    - Complex reasoning: [most capable model]
    - Resource-limited: [most efficient model]
    
    **Configuration Suggestions**:
    ```yaml
    # agents.yaml recommendations
    lighting-agent:
      model: mistral:7b  # Fast for simple decisions
    
    heating-agent:
      model: deepseek-r1:8b  # Better reasoning
    
    security-agent:
      model: gemini-pro  # Best quality for critical
    ```

## Expected Outcome
- Comprehensive benchmark report
- Performance comparison table
- Statistical analysis
- Model recommendations by use case
- Configuration optimization suggestions
- Cost analysis (if applicable)

## Benchmark Metrics

**Speed Metrics**:
- First token latency
- Total inference time
- Tokens per second
- Cold vs warm start

**Quality Metrics**:
- Decision accuracy
- JSON parsing success
- Instruction adherence
- Hallucination rate

**Resource Metrics**:
- Peak memory usage
- Average CPU utilization
- GPU usage (if applicable)
- Network latency

**Reliability Metrics**:
- Success rate
- Error frequency
- Timeout occurrences
- Connection stability

## Test Scenarios

**Simple** (baseline):
- Short prompt (<500 tokens)
- Single decision output
- No RAG retrieval

**Medium** (typical):
- Multi-room context
- Multiple options
- Basic reasoning required

**Complex** (stress test):
- Full entity context
- Multi-step reasoning
- RAG integration
- Long output required

## Hardware Considerations

**CPU-only**:
- Expect slower inference
- Lower memory bandwidth
- Consider quantized models

**GPU-accelerated**:
- Much faster inference
- Higher throughput
- VRAM limitations

**Cloud API**:
- Network latency added
- Cost considerations
- Rate limit awareness

## Benchmark Best Practices

- Run multiple iterations (10-20)
- Use consistent test data
- Measure cold and warm starts
- Test during normal load
- Account for system variance
- Document environment details
