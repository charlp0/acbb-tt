/**
 * ACBB TT — Génère le formulaire de signalement + sa feuille de réponses.
 *
 * UTILISATION (une seule fois) :
 *  1. Va sur https://script.google.com  →  "Nouveau projet"
 *  2. Colle TOUT ce fichier (remplace le contenu par défaut)
 *  3. Clique sur "Exécuter" (▷). Autorise l'accès à ton compte Google quand demandé.
 *  4. Ouvre le journal d'exécution (menu "Exécution" / Ctrl+Entrée) et copie le
 *     "LIEN VISITEURS" affiché. Envoie-le moi : je branche le bouton sur le site.
 */
function creerFormulaireSignalementACBB() {
  var form = FormApp.create('ACBB TT — Signaler une erreur ou une info')
    .setDescription("Tu as repéré un classement faux, un match manquant, une faute de nom… ? Signale-le ici, merci ! 🏓")
    .setConfirmationMessage("Merci ! Ton signalement a bien été envoyé — on corrige ça dès que possible.")
    .setCollectEmail(false)
    .setAllowResponseEdits(false)
    .setLimitOneResponsePerUser(false);

  form.addTextItem()
    .setTitle("Page ou joueur concerné")
    .setHelpText("Le nom du joueur, ou colle le lien de la page si tu peux.")
    .setRequired(false);

  form.addMultipleChoiceItem()
    .setTitle("Type de problème")
    .setChoiceValues([
      "Classement / niveau faux",
      "Résultat ou match faux",
      "Match manquant ou en trop",
      "Faute de nom / orthographe",
      "Autre"
    ])
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle("Décris le problème")
    .setHelpText("Le plus précis possible : ce qui est affiché vs ce qui devrait être.")
    .setRequired(true);

  form.addTextItem()
    .setTitle("Ton email (optionnel)")
    .setHelpText("Si tu veux qu'on te tienne au courant de la correction.")
    .setRequired(false);

  // Crée une feuille de calcul liée pour centraliser les réponses
  var ss = SpreadsheetApp.create("ACBB TT — Signalements (réponses)");
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  Logger.log("================ À COPIER ================");
  Logger.log("LIEN VISITEURS (à m'envoyer)  : " + form.getPublishedUrl());
  Logger.log("Lien d'édition du formulaire   : " + form.getEditUrl());
  Logger.log("Feuille des réponses           : " + ss.getUrl());
  Logger.log("==========================================");
}
