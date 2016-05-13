#include "rmsprop_op.h"
#include "caffe2/caffe2/core/common_gpu.h"
#include "caffe2/caffe2/core/context_gpu.h"

namespace caffe2 {

__global__ void RmsPropUpdate(
    int N,
    const float* g,
    const float* ms,
    const float* mom,
    float* ng,
    float* nms,
    float* nmom,
    float decay,
    float momentum,
    float epsilon,
    float learning_rate) {
  CUDA_1D_KERNEL_LOOP(i, N) {
    // Update new mean square estimate
    nms[i] = ms[i] + (1.0f - decay) * (g[i] * g[i] - ms[i]);
    // Update momentum estimate
    nmom[i] =
        mom[i] * momentum + learning_rate * g[i] / std::sqrt(epsilon + nms[i]);
    // New gradient is the momentum
    ng[i] = nmom[i];
  }
}

template <>
void rmsprop_update<CUDAContext>(
    int N,
    const float* g,
    const float* ms,
    const float* mom,
    float* ng,
    float* nms,
    float* nmom,
    float decay,
    float momentum,
    float epsilon,
    float learning_rate,
    CUDAContext* context) {
  RmsPropUpdate<<<CAFFE_GET_BLOCKS(N), CAFFE_CUDA_NUM_THREADS, 0, context->cuda_stream()>>>(
      N, g, ms, mom, ng, nms, nmom, decay, momentum, epsilon, learning_rate);
}


namespace {
REGISTER_CUDA_OPERATOR(RmsProp, RmsPropOp<float, CUDAContext>);
}

}
