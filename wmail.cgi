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

;; return the HTML output?
(defn send-logic [ch]
  (if (and (empty? @warning) (seq (:send ch)))
    (if (= "Preview" (:send ch))
      (do
        
        )
  )

;; returns ch, either unchanged, or with a new :send value
(defn check-and-confirm [ch]
  (when (= (:send ch) "Send")
    (let [testc (confirm ch)]
      (if (= testc (:confirm ch))
        (check-and-send ch)
        (do
          (warning "Please check your message.")
          (assoc ch :send "Edit"))))))

(defn main []
  ;; need to part CGI params
  ;; truncate everything to avoid buffer overflow attacks
  (let [params {}
        ch {:email1 (sanitize (:email1 params))
            :email2 (sanitize (:email2 params))
            :subject (sanitize (:subject params))
            :message (str/replace (:message params) #"\s+\Z" "")
            :send (:send params) ;; why aren't we cleaning this?
            :confirm (:confirm params) ;; ditto
            }]
    (when (seq (:send ch))
      (if (empty? (:email1 ch))
        (warning "Missing email. You must enter your email address so we can reply to you.")
        (when (!= (:email1 ch) (:email2 ch))
          (warning "Email addresses don't match."))))
    (let [chout (check-and-confirm ch)
          alltxt (send-logic chout)]
      (printf "Content-Type: text/html; charset=iso-8859-1\n\n%s\n" (template alltxt))
      )))

(comment

  )
