#pragma once

#include "caffe2/core/common_cudnn.h"
#include "caffe2/core/context.h"
#include "caffe2/core/context_gpu.h"
#include "caffe2/core/logging.h"
#include "caffe2/core/operator.h"

namespace caffe2 {

namespace detail {

template<typename T>
class TensorDescriptors {
 public:
  TensorDescriptors(
      size_t n,
      const std::vector<int>& dim,
      const std::vector<int>& stride);
  ~TensorDescriptors();
  const cudnnTensorDescriptor_t* descs() const { return descs_.data(); }
 private:
  std::vector<cudnnTensorDescriptor_t> descs_;
};

}

template <typename T>
class RecurrentBaseOp : public Operator<CUDAContext> {
 public:
  USE_OPERATOR_FUNCTIONS(CUDAContext);
  RecurrentBaseOp(const OperatorDef& operator_def, Workspace* ws);
  virtual ~RecurrentBaseOp();
  bool RunOnDevice() final {
    std::lock_guard<std::mutex> lock(cudnnWrapper_.mutex());
    bool success = RunWithCudnnWorkspace();
    // Since we will release the lock guard, we need to finish all the
    // device computation explicitly so the cudnn execution finishes.
    success &= context_.FinishDeviceComputation();
    return success;
  }

  virtual bool RunWithCudnnWorkspace() = 0;
 protected:
  void initialize(
      const Tensor<CUDAContext>& input,
      Tensor<CUDAContext>* dropoutStates,
      // If passed, reshapes to the appropriate size
      Tensor<CUDAContext>* output = nullptr,
      Tensor<CUDAContext>* hiddenOutput = nullptr,
      Tensor<CUDAContext>* cellOutput = nullptr);

  CuDNNWrapper cudnnWrapper_;
  cudnnDropoutDescriptor_t dropoutDesc_;
  cudnnRNNDescriptor_t rnnDesc_;
  cudnnFilterDescriptor_t wDesc_;
  cudnnTensorDescriptor_t hxDesc_;
  cudnnTensorDescriptor_t cxDesc_;
  cudnnTensorDescriptor_t hyDesc_;
  cudnnTensorDescriptor_t cyDesc_;

  std::unique_ptr<detail::TensorDescriptors<T>> xDesc_;
  std::unique_ptr<detail::TensorDescriptors<T>> yDesc_;

  std::vector<TIndex> cachedInputDims_;
  size_t reserveNbytes_;
  size_t cudnnWsNbytes_;

 private:
  DISABLE_COPY_AND_ASSIGN(RecurrentBaseOp);
};

#define USE_RECURRENT_BASE_FUNCTIONS          \
  USE_OPERATOR_FUNCTIONS(CUDAContext);        \
  using RecurrentBaseOp<T>::cudnnWrapper_;    \
  using RecurrentBaseOp<T>::dropoutDesc_;     \
  using RecurrentBaseOp<T>::rnnDesc_;         \
  using RecurrentBaseOp<T>::wDesc_;           \
  using RecurrentBaseOp<T>::hxDesc_;          \
  using RecurrentBaseOp<T>::cxDesc_;          \
  using RecurrentBaseOp<T>::hyDesc_;          \
  using RecurrentBaseOp<T>::cyDesc_;          \
  using RecurrentBaseOp<T>::xDesc_;           \
  using RecurrentBaseOp<T>::yDesc_;           \
  using RecurrentBaseOp<T>::cachedInputDims_; \
  using RecurrentBaseOp<T>::reserveNbytes_;   \
  using RecurrentBaseOp<T>::cudnnWsNbytes_;   \
  using RecurrentBaseOp<T>::initialize;

template <typename T>
class RecurrentOp : public RecurrentBaseOp<T> {
 public:
  USE_RECURRENT_BASE_FUNCTIONS
  RecurrentOp(const OperatorDef& operator_def, Workspace* ws)
      : RecurrentBaseOp<T>(operator_def, ws) {}

  virtual bool RunWithCudnnWorkspace() override;
 protected:
  INPUT_TAGS(INPUT, HIDDEN_INPUT, CELL_INPUT, WEIGHT);
  OUTPUT_TAGS(OUTPUT, HIDDEN_OUTPUT, CELL_OUTPUT, RNN_SCRATCH, DROPOUT_STATES);
  DISABLE_COPY_AND_ASSIGN(RecurrentOp);
};

template <typename T>
class RecurrentGradientOp : public RecurrentBaseOp<T> {
 public:
  USE_RECURRENT_BASE_FUNCTIONS
  RecurrentGradientOp(const OperatorDef& operator_def, Workspace* ws)
      : RecurrentBaseOp<T>(operator_def, ws) {}

  virtual bool RunWithCudnnWorkspace() override;
 protected:
  INPUT_TAGS(
      INPUT,
      HIDDEN_INPUT,
      CELL_INPUT,
      WEIGHT,
      RNN_SCRATCH,
      OUTPUT,
      GRAD_OUTPUT,
      GRAD_HIDDEN_OUTPUT,
      GRAD_CELL_OUTPUT);
  OUTPUT_TAGS(
      GRAD_INPUT,
      GRAD_HIDDEN_INPUT,
      GRAD_CELL_INPUT,
      GRAD_WEIGHT,
      DROPOUT_STATES);
  DISABLE_COPY_AND_ASSIGN(RecurrentGradientOp);
};

template <typename T>
class RecurrentInitOp : public RecurrentBaseOp<T> {
 public:
  USE_RECURRENT_BASE_FUNCTIONS
  RecurrentInitOp(const OperatorDef& operator_def, Workspace* ws)
      : RecurrentBaseOp<T>(operator_def, ws) {}

  virtual bool RunWithCudnnWorkspace() override;
 protected:
  INPUT_TAGS(INPUT);
  OUTPUT_TAGS(WEIGHT, DROPOUT_STATES);
};

}
