#!/usr/bin/env bb
;; -*-clojure-*- This sets Emacs mode

(def config-file (str (fs/home) "/.wmail-config"))

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

(confmap)
