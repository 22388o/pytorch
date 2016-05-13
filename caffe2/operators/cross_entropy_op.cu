#include "caffe2/core/context_gpu.h"
#include "caffe2/operators/cross_entropy_op.h"

namespace caffe2 {

namespace {
__global__ void LabelCrossEntropyKernel(
    const int N, const int D, const float* Xdata, const int* labeldata,
    const float log_threshold, float* Ydata) {
  CUDA_1D_KERNEL_LOOP(i, N) {
    Ydata[i] = -logf(max(Xdata[i * D + labeldata[i]], log_threshold));
  }
}
__global__ void LabelCrossEntropyGradientKernel(
    const int N, const int D, const float* Xdata, const int* labeldata,
    const float* dYdata, const float log_threshold, float* dXdata) {
  CUDA_1D_KERNEL_LOOP(i, N) {
    int idx = i * D + labeldata[i];
    dXdata[idx] = - dYdata[i] / max(Xdata[idx], log_threshold);
  }
}
}  // namespace

template <>
bool LabelCrossEntropyOp<float, CUDAContext>::RunOnDevice() {
  auto& X = Input(0);
  auto& label = Input(1);
  auto* Y = Output(0);
  CAFFE_DCHECK_EQ(X.ndim(), 2);
  int N = X.dim32(0);
  int D = X.dim32(1);
  CAFFE_DCHECK_EQ(label.ndim(), 1);
  CAFFE_DCHECK_EQ(label.dim32(0), N);
  Y->Reshape(vector<TIndex>(1, N));
  LabelCrossEntropyKernel<<<CAFFE_GET_BLOCKS(N), CAFFE_CUDA_NUM_THREADS,
                            0, context_.cuda_stream()>>>(
      N, D, X.data<float>(), label.data<int>(), kLOG_THRESHOLD(), Y->mutable_data<float>());
  return true;
}

template <>
bool LabelCrossEntropyGradientOp<float, CUDAContext>::RunOnDevice() {
  auto& X = Input(0);
  auto& label = Input(1);
  auto& dY = Input(2);
  auto* dX = Output(0);
  CAFFE_DCHECK_EQ(X.ndim(), 2);
  int N = X.dim32(0);
  int D = X.dim32(1);
  CAFFE_DCHECK_EQ(label.ndim(), 1);
  CAFFE_DCHECK_EQ(label.dim32(0), N);
  CAFFE_DCHECK_EQ(dY.ndim(), 1);
  CAFFE_DCHECK_EQ(dY.dim32(0), N);
  dX->ReshapeLike(X);
  math::Set<float, CUDAContext>(
      dX->size(), 0.f, dX->mutable_data<float>(), &context_);
  LabelCrossEntropyGradientKernel<<<CAFFE_GET_BLOCKS(N), CAFFE_CUDA_NUM_THREADS,
                                    0, context_.cuda_stream()>>>(
      N, D, X.data<float>(), label.data<int>(), dY.data<float>(), kLOG_THRESHOLD(),
      dX->mutable_data<float>());
  return true;
}

namespace {
__global__ void MakeTwoClassKernel(
    const int N, const float* Xdata, float* Ydata) {
  CUDA_1D_KERNEL_LOOP(i, N) {
    Ydata[i * 2] = 1.0 - Xdata[i];
    Ydata[i * 2 + 1] = Xdata[i];
  }
}
__global__ void MakeTwoClassGradientKernel(
    const int N, const float* dYdata, float* dXdata) {
  CUDA_1D_KERNEL_LOOP(i, N) {
    dXdata[i] = dYdata[i * 2 + 1] - dYdata[i * 2];
  }
}
}  // namespace

template <>
bool MakeTwoClassOp<float, CUDAContext>::RunOnDevice() {
  auto& X = Input(0);
  auto* Y = Output(0);
  auto shape = X.dims();
  shape.push_back(2);
  CAFFE_CHECK_LT(X.size(), std::numeric_limits<int>::max() / 2);
  Y->Reshape(shape);
  int N = X.size();
  MakeTwoClassKernel<<<CAFFE_GET_BLOCKS(N), CAFFE_CUDA_NUM_THREADS,
                       0, context_.cuda_stream()>>>(
      N, X.data<float>(), Y->mutable_data<float>());
  return true;
}

template <>
bool MakeTwoClassGradientOp<float, CUDAContext>::RunOnDevice() {
  auto& dY = Input(0);
  auto* dX = Output(0);
  auto shape = dY.dims();
  CAFFE_CHECK_GE(shape.size(), 1);
  CAFFE_CHECK_EQ(shape.back(), 2);
  shape.pop_back();
  CAFFE_CHECK_LT(dY.size(), std::numeric_limits<int>::max());
  dX->Reshape(shape);
  int N = dX->size();
  MakeTwoClassGradientKernel<<<CAFFE_GET_BLOCKS(N), CAFFE_CUDA_NUM_THREADS,
                               0, context_.cuda_stream()>>>(
      N, dY.data<float>(), dX->mutable_data<float>());
  return true;
}

namespace {
REGISTER_CUDA_OPERATOR(LabelCrossEntropy,
                       LabelCrossEntropyOp<float, CUDAContext>);
REGISTER_CUDA_OPERATOR(LabelCrossEntropyGradient,
                       LabelCrossEntropyGradientOp<float, CUDAContext>);

REGISTER_CUDA_OPERATOR(MakeTwoClass,
                       MakeTwoClassOp<float, CUDAContext>);
REGISTER_CUDA_OPERATOR(MakeTwoClassGradient,
                       MakeTwoClassGradientOp<float, CUDAContext>);
}  // namespace
}  // namespace caffe2
