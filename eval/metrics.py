def precision(true_positive , false_positive):
  total = true_positive + false_positive

  if total == 0 :
    return 0
  
  return true_positive / total


def recall(true_positive , false_positive):
  total = true_positive + false_positive

  if total == 0:
    return 0
  
  return true_positive/total

def f1_score(precision_value , recall_value):
  total = precision_value + recall_value

  if total == 0:
    return 0
  
  return 2 * (precision_value * recall_value)/total

def matching_accuracy(correct_matches , total_matches):
  if total_matches == 0:
    return 0
  
  return correct_matches / total_matches


def escalation_accuracy(correct_escalations , total_escalations):
  if total_escalations == 0:
    return 0
  
  return correct_escalations / total_escalations

if __name__ == "__main__":

  tp = 8 
  fp = 2
  fn = 1

  precision_result = precision(tp , fp)
  recall_result = recall(tp , fn)

  f1_result = f1_score(precision_result,recall_result)

  match_result= matching_accuracy(9,10)

  escalation_result= escalation_accuracy(4,5)

  print("DonorLoop Evaluation")
  print("=====================")

  print("Precision:", round(precision_result, 2))
  print("Recall:", round(recall_result, 2))
  print("F1 Score:", round(f1_result, 2))
  print("Matching Accuracy:", round(match_result, 2))
  print("Escalation Accuracy:", round(escalation_result, 2))