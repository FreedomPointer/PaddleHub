#coding:utf-8
#   Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Fine-tuning on classification task """

import argparse
import ast
import paddlehub as hub

# yapf: disable
parser = argparse.ArgumentParser(__doc__)
parser.add_argument("--num_epoch", type=int, default=3, help="Number of epoches for fine-tuning.")
parser.add_argument("--use_gpu", type=ast.literal_eval, default=True, help="Whether use GPU for fine-tuning, input should be True or False")
parser.add_argument("--learning_rate", type=float, default=5e-5, help="Learning rate used to train with warmup.")
parser.add_argument("--weight_decay", type=float, default=0.01, help="Weight decay rate for L2 regularizer.")
parser.add_argument("--warmup_proportion", type=float, default=0.1, help="Warmup proportion params for warmup strategy")
parser.add_argument("--checkpoint_dir", type=str, default=None, help="Directory to model checkpoint")
parser.add_argument("--max_seq_len", type=int, default=512, help="Number of words of the longest seqence.")
parser.add_argument("--batch_size", type=int, default=32, help="Total examples' number in batch for training.")
parser.add_argument("--network", type=str, default='bilstm', help="Pre-defined network which was connected after Transformer model, such as ERNIE, BERT ,RoBERTa and ELECTRA.")
parser.add_argument("--use_data_parallel", type=ast.literal_eval, default=False, help="Whether use data parallel.")
args = parser.parse_args()
# yapf: enable.

if __name__ == '__main__':

    # Load Paddlehub ERNIE Tiny pretrained model
    module = hub.Module(name="ernie_tiny")
    inputs, outputs, program = module.context(
        trainable=True, max_seq_len=args.max_seq_len)

    # Download dataset and use accuracy as metrics
    # Choose dataset: GLUE/XNLI/ChinesesGLUE/NLPCC-DBQA/LCQMC
    # metric should be acc, f1 or matthews
    dataset = hub.dataset.ChnSentiCorp()
    metrics_choices = ["acc"]

    # For ernie_tiny, it use sub-word to tokenize chinese sentence
    # If not ernie tiny, sp_model_path and word_dict_path should be set None
    reader = hub.reader.ClassifyReader(
        dataset=dataset,
        vocab_path=module.get_vocab_path(),
        max_seq_len=args.max_seq_len,
        sp_model_path=module.get_spm_path(),
        word_dict_path=module.get_word_dict_path())

    # Construct transfer learning network
    # Use "pooled_output" for classification tasks on an entire sentence.
    # Use "sequence_output" for token-level output.
    token_feature = outputs["sequence_output"]

    # Setup feed list for data feeder
    # Must feed all the tensor of module need
    feed_list = [
        inputs["input_ids"].name,
        inputs["position_ids"].name,
        inputs["segment_ids"].name,
        inputs["input_mask"].name,
    ]

    # Select fine-tune strategy, setup config and fine-tune
    strategy = hub.AdamWeightDecayStrategy(
        warmup_proportion=args.warmup_proportion,
        weight_decay=args.weight_decay,
        learning_rate=args.learning_rate)

    # Setup RunConfig for PaddleHub Fine-tune API
    config = hub.RunConfig(
        use_data_parallel=args.use_data_parallel,
        use_cuda=args.use_gpu,
        num_epoch=args.num_epoch,
        batch_size=args.batch_size,
        checkpoint_dir=args.checkpoint_dir,
        strategy=strategy)

    # Define a classfication fine-tune task by PaddleHub's API
    # network choice: bilstm, bow, cnn, dpcnn, gru, lstm (PaddleHub pre-defined network)
    # If you wanna add network after ERNIE/BERT/RoBERTa/ELECTRA module,
    # you must use the outputs["sequence_output"] as the token_feature of TextClassifierTask,
    # rather than outputs["pooled_output"], and feature is None
    cls_task = hub.TextClassifierTask(
        data_reader=reader,
        token_feature=token_feature,
        feed_list=feed_list,
        network=args.network,
        num_classes=dataset.num_labels,
        config=config,
        metrics_choices=metrics_choices)

    # Fine-tune and evaluate by PaddleHub's API
    # will finish training, evaluation, testing, save model automatically
    cls_task.finetune_and_eval()
