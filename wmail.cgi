#!/usr/bin/env bb
;; -*-clojure-*- This sets Emacs mode

(def config-file (str (fs/home) "/.wmail-config"))

(defn sanitize [dirty]
  (->
   (subs dirty 0 (min (count dirty) 50))
   (str/replace #";" "")
   (str/replace #"[\000-\037]" "")))


;; clean up individual lines from config. For a comment, return an empty string.
(defn clean-up [dirty]
  (-> dirty
      (str/replace #"#.*\n*$" "")
      (str/replace #"\s*=\s*" "=")
      (str/replace #"\s+\n" "\n")
      (str/replace #"(?s)\s+$" "")
      (str/replace #"^\s+" "")))

(defn read-config []
  (if (fs/exists? config-file)
    (remove empty? (map clean-up (fs/read-all-lines config-file)))
    []))

(defn split-nv [confline]
  (let [nv (re-matches #"(.*)=(.*)" confline)]
    [(keyword (nth nv 1)) (nth nv 2)]))

(defn confmap []
  (into {} (mapv split-nv (read-config))))

(def warnmsg (atom ""))

(defn warning [msg]
  (swap! warnmsg str "\n" msg))

(reset! warnmsg "")

(defn confirm [config ch]
  (str/replace (:out (shell/sh "echo" (:random_string config) (:message ch) "|" "/usr/bin/md5sum"))
               #"\s+(.*)"
               ""))

;; Return cf, modified with a :template value
;; Might better be called determint-template-name
(defn send-logic [ch cf]
  (if (and (empty? @warning) (seq (:send ch)))
    (cond (= "Preview" (:send ch))
          (assoc cf :confirm (confirm ch) :template "wmail_2.html")
          (= "Edit" (:send ch))
          (assoc cf :template "wmail_1.html")
          (= "Send" (:send ch))
          (assoc cf :template "wmail_thanks.html"))
    (assoc cf :template "wmail_1.html")))

;; Side effecty. Log the message, and call sendmail.
(defn send [ch cf]
  (let [full-msg (str (format "To: %s\n" (:mail_to ch))
                      (format "X-remote-addr: %s\n" (:REMOTE_ADDR ch)) ;; $ENV{REMOTE_ADDR}
                      (format "X-user-agent: %s\n" (:HTTP_USER_AGENT ch)) ;; $ENV{HTTP_USER_AGENT}
                      (format "From: %s\n" (:from cf))
                      (format "Reply-To: %s\n" (:email1 ch))
                      (format "Subject: %s %s\n\n" (:subject_prefix cf) (:subject ch))
                      (format "%s\n" (:message ch)))]
    ;; log the message
    (spit (:email_log cf) full-msg :append true)
    ;; call sendmail
    
  ))
(comment
  ;; works 
  (shell/sh "sh" "-c" "tail readme.txt | cat > tmp.txt")

  ;; doesn't work?
  require '[babashka.process :refer [process check sh pipeline pb]])
  (mapv :out (pipeline (pb '[ls]) (pb '[cat])))
  (-> (pipeline (pb ["ls"]) (pb ["cat"])) last :out slurp)
  
  (pipeline (pb '[tail "readme.txt"])
            (pb '[cat > tmp.txt]))

  (pipeline (pb '[tail -f "readme.txt"])
            (pb '[cat])
            (pb '[grep "5"] {:out :inherit}))
  
  )

;; returns ch, either unchanged, or with a new :send value
(defn check-and-confirm [ch cf]
  (when (= (:send ch) "Send")
    (let [testc (confirm ch)]
      (if (= testc (:confirm ch))
        (do
          (send ch cf)
          ch)
        (do
          (warning "Please check your message.")
          (assoc ch :send "Edit"))))))

;; Deep in the past,  #"\\([0-9]{3})" was replaced by the actual octal character.
;; There was probably some character I wanted to subsutite in HTML. Dunno why.
;; Order of the merge is important. cf-final (config read locally) must be last so it's keys
;; override any duplicates in ch (http params). 
(defn template [ch-final cf-final]
  (let [cx (merge ch-final cf-final)]
  (str/replace (slurp (:template cx))
               #"(?<!\\)\$([\w\d]+)(?!=\w)(?!=\d)(?!=\z)"
               #((keyword (%1 2)) cx))))


;; Keep ch (http params) separate from cf (config values) so that http params can't easily overwrite
;; internal config.
(defn main []
  ;; need to part CGI params
  ;; truncate everything to avoid buffer overflow attacks
  (let [params {}
        ch {:email1 (sanitize (:email1 params))
             :email2 (sanitize (:email2 params))
             :subject (sanitize (:subject params))
             :message (str/replace (:message params) #"\s+\Z" "")
             :send (:send params) ;; why not clean this?
             :confirm (:confirm params)} ;; why not clean this?
        cf (confmap)]
    (when (seq (:send ch))
      (if (empty? (:email1 ch))
        (warning "Missing email. You must enter your email address so we can reply to you.")
        (when (!= (:email1 ch) (:email2 ch))
          (warning "Email addresses don't match."))))
    (let [ch-final (check-and-confirm ch cf)
          cf-final (send-logic ch-final cf)]
      (printf "Content-Type: text/html; charset=iso-8859-1\n\n%s\n" (template ch-final cf-final))
      )))

