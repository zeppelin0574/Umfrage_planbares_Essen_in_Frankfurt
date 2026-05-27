(function () {
  var submittedKey = "lunch_survey_submitted";

  if (document.body.dataset.surveySubmitted === "true") {
    localStorage.setItem(submittedKey, "true");
    return;
  }

  var form = document.getElementById("survey-form");
  var notice = document.getElementById("duplicate-notice");
  var content = document.getElementById("survey-content");
  var participateAgain = document.getElementById("participate-again");

  if (!form || !notice || !content || !participateAgain) {
    return;
  }

  if (localStorage.getItem(submittedKey) === "true") {
    notice.hidden = false;
    content.hidden = true;
  }

  participateAgain.addEventListener("click", function () {
    notice.hidden = true;
    content.hidden = false;
  });
})();
